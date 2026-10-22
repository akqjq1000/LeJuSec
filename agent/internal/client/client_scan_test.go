package client

import (
	"crypto/ed25519"
	"crypto/rand"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/akqjq1000/LeJuSec/agent/internal/scan"
)

func TestSendScan(t *testing.T) {
	var gotPath, gotSig string
	var gotBody []byte
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotPath = r.URL.Path
		gotSig = r.Header.Get("X-Signature")
		gotBody, _ = io.ReadAll(r.Body)
		w.WriteHeader(http.StatusCreated)
	}))
	defer srv.Close()

	_, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatal(err)
	}

	passed := false
	findings := []scan.Finding{
		{Tool: "openscap", CheckID: "rule_x", Passed: &passed},
		{Tool: "trivy", CheckID: "CVE-1", Severity: "high"},
	}
	if err := New(srv.URL, nil).SendScan(7, priv, findings); err != nil {
		t.Fatalf("SendScan: %v", err)
	}

	if gotPath != "/assets/7/scan" {
		t.Fatalf("unexpected path %q", gotPath)
	}
	if gotSig == "" {
		t.Fatal("missing X-Signature header")
	}
	var payload struct {
		Findings []scan.Finding `json:"findings"`
	}
	if err := json.Unmarshal(gotBody, &payload); err != nil {
		t.Fatal(err)
	}
	if len(payload.Findings) != 2 || payload.Findings[1].CheckID != "CVE-1" {
		t.Fatalf("unexpected findings: %+v", payload.Findings)
	}
}
