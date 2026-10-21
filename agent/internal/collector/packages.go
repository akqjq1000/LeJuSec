package collector

import (
	"os/exec"
	"strings"
)

// Package describes a single installed package.
type Package struct {
	Name    string `json:"name"`
	Version string `json:"version"`
	Source  string `json:"source"` // "dpkg", "rpm", "pacman", "source"
}

// Packages returns installed packages discovered via the host package manager.
// Detection order: dpkg (Debian/Ubuntu), rpm (RHEL/SUSE), pacman (Arch).
// Returns an empty slice when no supported package manager is present.
func Packages() ([]Package, error) {
	if path, err := exec.LookPath("dpkg-query"); err == nil {
		out, err := exec.Command(path, "-W", "-f=${Package}\t${Version}\n").Output()
		if err != nil {
			return nil, err
		}
		return parseDpkg(string(out)), nil
	}
	if path, err := exec.LookPath("rpm"); err == nil {
		out, err := exec.Command(path, "-qa", "--qf", "%{NAME}\t%{VERSION}-%{RELEASE}\n").Output()
		if err != nil {
			return nil, err
		}
		return parseRPM(string(out)), nil
	}
	if path, err := exec.LookPath("pacman"); err == nil {
		out, err := exec.Command(path, "-Q").Output()
		if err != nil {
			return nil, err
		}
		return parsePacman(string(out)), nil
	}
	return []Package{}, nil
}

// parseDpkg parses tab-separated "name<TAB>version" lines (dpkg-query -W).
func parseDpkg(out string) []Package {
	return parseTabbed(out, "dpkg")
}

// parseRPM parses tab-separated "name<TAB>version" lines (rpm -qa --qf).
func parseRPM(out string) []Package {
	return parseTabbed(out, "rpm")
}

func parseTabbed(out, source string) []Package {
	pkgs := make([]Package, 0)
	for _, line := range strings.Split(out, "\n") {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		name, version, ok := strings.Cut(line, "\t")
		if !ok || name == "" {
			continue
		}
		pkgs = append(pkgs, Package{Name: name, Version: version, Source: source})
	}
	return pkgs
}

// parsePacman parses space-separated "name version" lines (pacman -Q).
func parsePacman(out string) []Package {
	pkgs := make([]Package, 0)
	for _, line := range strings.Split(out, "\n") {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		name, version, ok := strings.Cut(line, " ")
		if !ok || name == "" {
			continue
		}
		pkgs = append(pkgs, Package{Name: name, Version: strings.TrimSpace(version), Source: "pacman"})
	}
	return pkgs
}
