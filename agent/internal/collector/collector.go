// Package collector gathers inventory from the target system: installed
// packages, running processes, and their associated config/log files.
package collector

// Package describes a single installed package.
type Package struct {
	Name    string
	Version string
	Source  string // "rpm", "dpkg", "pacman", "source"
}

// Packages returns installed packages discovered on the host.
//
// Phase 1 skeleton: the real implementation shells out to the platform
// package manager (rpm -qa / dpkg -l / pacman -Q) and parses its output.
// See docs/design/features.md (기능 2).
func Packages() ([]Package, error) {
	return []Package{}, nil
}
