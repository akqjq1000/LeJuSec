package collector

import "testing"

func TestPackagesSkeleton(t *testing.T) {
	pkgs, err := Packages()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(pkgs) != 0 {
		t.Fatalf("expected 0 packages from skeleton, got %d", len(pkgs))
	}
}
