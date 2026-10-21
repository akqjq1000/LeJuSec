package collector

import (
	"os"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
)

// Process describes a running process observed on the host.
type Process struct {
	PID  int    `json:"pid"`
	Name string `json:"name"`
	Exe  string `json:"exe"`
}

// Processes returns running processes. Implemented via /proc on Linux;
// returns an empty slice on other platforms.
func Processes() ([]Process, error) {
	if runtime.GOOS != "linux" {
		return []Process{}, nil
	}
	return readProcProcesses("/proc")
}

func readProcProcesses(procRoot string) ([]Process, error) {
	entries, err := os.ReadDir(procRoot)
	if err != nil {
		return nil, err
	}
	procs := make([]Process, 0)
	for _, e := range entries {
		pid, err := strconv.Atoi(e.Name())
		if err != nil {
			continue // not a PID directory
		}
		name := ""
		if data, err := os.ReadFile(filepath.Join(procRoot, e.Name(), "stat")); err == nil {
			name = parseStatComm(string(data))
		}
		exe, _ := os.Readlink(filepath.Join(procRoot, e.Name(), "exe"))
		procs = append(procs, Process{PID: pid, Name: name, Exe: exe})
	}
	return procs, nil
}

// parseStatComm extracts the process name (comm) from /proc/<pid>/stat.
// Format is "pid (comm) state ...". comm itself may contain spaces and
// parentheses, so the name is the text between the first '(' and last ')'.
func parseStatComm(stat string) string {
	start := strings.IndexByte(stat, '(')
	end := strings.LastIndexByte(stat, ')')
	if start < 0 || end < 0 || end <= start {
		return ""
	}
	return stat[start+1 : end]
}
