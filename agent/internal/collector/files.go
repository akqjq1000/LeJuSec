package collector

import (
	"os/exec"
	"strings"
)

// PackageFiles returns the files owned by a package. This is the input for
// associated config/log discovery (기능 2). Uses dpkg -L or rpm -ql depending
// on availability; returns an empty slice when unsupported.
func PackageFiles(name string) ([]string, error) {
	if path, err := exec.LookPath("dpkg"); err == nil {
		out, err := exec.Command(path, "-L", name).Output()
		if err != nil {
			return nil, err
		}
		return parseFileList(string(out)), nil
	}
	if path, err := exec.LookPath("rpm"); err == nil {
		out, err := exec.Command(path, "-ql", name).Output()
		if err != nil {
			return nil, err
		}
		return parseFileList(string(out)), nil
	}
	return []string{}, nil
}

func parseFileList(out string) []string {
	files := make([]string, 0)
	for _, line := range strings.Split(out, "\n") {
		line = strings.TrimSpace(line)
		if line == "" || line == "(contains no files)" {
			continue
		}
		files = append(files, line)
	}
	return files
}
