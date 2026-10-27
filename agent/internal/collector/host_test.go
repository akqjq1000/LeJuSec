package collector

import (
	"net"
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

func TestParseOSRelease(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "os-release")
	content := `NAME="Ubuntu"
ID=ubuntu
VERSION_ID="24.04"
PRETTY_NAME="Ubuntu 24.04 LTS"
`
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
	id, version := parseOSRelease(path)
	if id != "ubuntu" {
		t.Errorf("ID = %q, want ubuntu", id)
	}
	if version != "24.04" {
		t.Errorf("VERSION_ID = %q, want 24.04", version)
	}
}

func TestParseOSReleaseMissing(t *testing.T) {
	id, version := parseOSRelease(filepath.Join(t.TempDir(), "nope"))
	if id != "" || version != "" {
		t.Errorf("missing file should yield empty, got %q/%q", id, version)
	}
}

func TestDetectHostAlwaysPopulated(t *testing.T) {
	host := DetectHost()
	if host.Family != runtime.GOOS {
		t.Errorf("Family = %q, want %q", host.Family, runtime.GOOS)
	}
	if host.Arch != runtime.GOARCH {
		t.Errorf("Arch = %q, want %q", host.Arch, runtime.GOARCH)
	}
	// OS는 어떤 플랫폼에서도 비어 있지 않아야 한다(탐지 실패 시 GOOS로 폴백).
	if host.OS == "" {
		t.Error("OS should never be empty")
	}
	// hostname은 os.Hostname()으로 거의 항상 채워진다(서버가 자동 등록에 사용).
	if host.Hostname == "" {
		t.Error("Hostname should be populated")
	}
	// Address는 네트워크가 없는 환경에서 빈 값일 수 있으나, 있으면 파싱 가능한 IP여야 한다.
	if host.Address != "" && net.ParseIP(host.Address) == nil {
		t.Errorf("Address = %q, not a valid IP", host.Address)
	}
}
