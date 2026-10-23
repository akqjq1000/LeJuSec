package client

import (
	"crypto/ed25519"
	"crypto/rand"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestPullCommands(t *testing.T) {
	var gotPath, gotSig string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotPath = r.URL.Path
		gotSig = r.Header.Get("X-Signature")
		_ = json.NewEncoder(w).Encode([]AgentCommand{{ID: 3, Kind: "scan"}})
	}))
	defer srv.Close()

	_, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatal(err)
	}

	commands, err := New(srv.URL, nil).PullCommands(9, priv)
	if err != nil {
		t.Fatalf("PullCommands: %v", err)
	}
	if gotPath != "/assets/9/commands/pull" {
		t.Fatalf("unexpected path %q", gotPath)
	}
	if gotSig == "" {
		t.Fatal("missing X-Signature header")
	}
	if len(commands) != 1 || commands[0].ID != 3 || commands[0].Kind != "scan" {
		t.Fatalf("unexpected commands: %+v", commands)
	}
}

func TestReportCommands(t *testing.T) {
	var gotPath string
	var gotBody []byte
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotPath = r.URL.Path
		gotBody, _ = io.ReadAll(r.Body)
		w.WriteHeader(http.StatusOK)
	}))
	defer srv.Close()

	_, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatal(err)
	}

	results := []CommandResult{{ID: 3, Status: "done", Result: "2 findings"}}
	if err := New(srv.URL, nil).ReportCommands(9, priv, results); err != nil {
		t.Fatalf("ReportCommands: %v", err)
	}
	if gotPath != "/assets/9/commands/report" {
		t.Fatalf("unexpected path %q", gotPath)
	}
	var payload struct {
		Results []CommandResult `json:"results"`
	}
	if err := json.Unmarshal(gotBody, &payload); err != nil {
		t.Fatal(err)
	}
	if len(payload.Results) != 1 || payload.Results[0].Status != "done" {
		t.Fatalf("unexpected results: %+v", payload.Results)
	}
}
