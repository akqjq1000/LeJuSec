package collector

import "testing"

func TestCollect(t *testing.T) {
	inv, err := Collect()
	if err != nil {
		t.Fatalf("Collect returned error: %v", err)
	}
	// Package/process counts are environment-dependent; ensure the snapshot
	// is well-formed (non-nil slices) so JSON output is always a list.
	if inv.Packages == nil {
		t.Fatal("expected non-nil Packages slice")
	}
	if inv.Processes == nil {
		t.Fatal("expected non-nil Processes slice")
	}
}
