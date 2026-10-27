package collector

import (
	"net"
	"os"
	"runtime"
	"strings"
)

// Host describes the detected identity of the target (OS, hostname, address).
// It is collected automatically so operators never type the OS or hostname when
// registering an asset; the control plane fills the asset's os/os_version,
// hostname and address from the signed inventory once the agent first reports.
type Host struct {
	Hostname  string `json:"hostname"`   // os.Hostname()
	Address   string `json:"address"`    // preferred outbound IPv4, when detectable
	OS        string `json:"os"`         // distro id (ubuntu, rhel, debian…) or GOOS
	OSVersion string `json:"os_version"` // VERSION_ID (e.g. "24.04") when known
	Family    string `json:"family"`     // "linux" | "darwin" | "windows" | …
	Arch      string `json:"arch"`       // GOARCH (amd64, arm64…)
}

// osReleasePath is overridable in tests. On Linux it points at the standard
// os-release location.
var osReleasePath = "/etc/os-release"

// DetectHost best-effort identifies the operating system. On Linux it parses
// /etc/os-release (ID + VERSION_ID); everywhere else it falls back to the Go
// runtime's GOOS. It never returns an error: unknown fields stay empty so the
// agent and control plane degrade gracefully.
func DetectHost() Host {
	host := Host{Family: runtime.GOOS, Arch: runtime.GOARCH}
	if runtime.GOOS == "linux" {
		id, version := parseOSRelease(osReleasePath)
		host.OS = id
		host.OSVersion = version
	}
	if host.OS == "" {
		// darwin/windows, or os-release missing: use the platform family.
		host.OS = runtime.GOOS
	}
	if name, err := os.Hostname(); err == nil {
		host.Hostname = name
	}
	host.Address = localAddress()
	return host
}

// localAddress returns the preferred outbound IPv4 of this host, or "" when it
// cannot be determined. It opens a UDP socket to a public address but sends
// nothing — the kernel picks the source IP the host would use to route out.
func localAddress() string {
	conn, err := net.Dial("udp", "8.8.8.8:80")
	if err != nil {
		return ""
	}
	defer func() { _ = conn.Close() }()
	if addr, ok := conn.LocalAddr().(*net.UDPAddr); ok {
		return addr.IP.String()
	}
	return ""
}

// parseOSRelease returns the ID and VERSION_ID values from an os-release file.
// Missing file or keys yield empty strings.
func parseOSRelease(path string) (id, version string) {
	data, err := os.ReadFile(path)
	if err != nil {
		return "", ""
	}
	for _, line := range strings.Split(string(data), "\n") {
		key, value, ok := strings.Cut(strings.TrimSpace(line), "=")
		if !ok {
			continue
		}
		value = strings.Trim(strings.TrimSpace(value), `"'`)
		switch key {
		case "ID":
			id = value
		case "VERSION_ID":
			version = value
		}
	}
	return id, version
}
