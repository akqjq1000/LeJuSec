// Package collector gathers inventory from the target system: installed
// packages, running processes, and their associated config/log files.
//
// Phase 1: real collection on Linux hosts (shelling out to the package
// manager and reading /proc). On unsupported platforms collection returns
// empty results without error, so the agent stays buildable everywhere.
package collector

// Inventory is a point-in-time snapshot collected from a host.
type Inventory struct {
	Packages  []Package `json:"packages"`
	Processes []Process `json:"processes"`
}

// Collect gathers a full inventory snapshot.
func Collect() (Inventory, error) {
	pkgs, err := Packages()
	if err != nil {
		return Inventory{}, err
	}
	procs, err := Processes()
	if err != nil {
		return Inventory{}, err
	}
	return Inventory{Packages: pkgs, Processes: procs}, nil
}
