// Package remediate applies approved remediation scripts on the target and
// rolls back on failure. A local denylist re-checks the script before running
// (defense in depth; the control plane already gates with static analysis).
package remediate

import (
	"context"
	"os/exec"
	"strings"
	"time"
)

// Result is the outcome of applying one remediation.
type Result struct {
	ID     int    `json:"id"`
	Status string `json:"status"` // applied | rolled_back | failed | skipped
	Output string `json:"output"`
}

// Runner executes a shell script and returns its combined output.
type Runner func(script string) (string, error)

// ShellRunner runs scripts via `sh -c` with a timeout (production runner).
func ShellRunner(timeout time.Duration) Runner {
	return func(script string) (string, error) {
		ctx, cancel := context.WithTimeout(context.Background(), timeout)
		defer cancel()
		out, err := exec.CommandContext(ctx, "sh", "-c", script).CombinedOutput()
		return string(out), err
	}
}

var dangerousSubstrings = []string{
	"rm -rf", "rm -fr", "rm -r -f", "rm -f -r",
	"dd of=/dev/", "mkfs", "shutdown", "reboot", "poweroff", "halt",
	"userdel", "deluser", ":(){", "/dev/sd", "/dev/nvme", "iptables -f",
}

func isDangerous(script string) bool {
	low := strings.ToLower(script)
	for _, s := range dangerousSubstrings {
		if strings.Contains(low, s) {
			return true
		}
	}
	return false
}

func trunc(s string) string {
	s = strings.ReplaceAll(strings.TrimSpace(s), "\n", " ")
	if len(s) > 200 {
		return s[:200]
	}
	return s
}

// Apply runs the remediation script; on failure it runs the rollback.
func Apply(id int, script, rollback string, run Runner) Result {
	if isDangerous(script) {
		return Result{ID: id, Status: "skipped", Output: "local denylist blocked script"}
	}
	out, err := run(script)
	if err == nil {
		return Result{ID: id, Status: "applied", Output: trunc(out)}
	}
	applyErr := err.Error()
	if _, rbErr := run(rollback); rbErr == nil {
		return Result{ID: id, Status: "rolled_back", Output: trunc("apply failed (" + applyErr + "); rolled back")}
	}
	return Result{ID: id, Status: "failed", Output: trunc("apply and rollback failed (" + applyErr + ")")}
}
