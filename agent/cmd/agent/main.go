// Command agent is the LeJuSec target-system agent.
//
// Phase 1: collects a host inventory (packages, processes) and prints it as
// JSON. Scanning, FIM, and signed transport are added per docs/roadmap.md.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"

	"github.com/akqjq1000/LeJuSec/agent/internal/collector"
)

// version is injected at build time via -ldflags "-X main.version=...".
var version = "dev"

func main() {
	showVersion := flag.Bool("version", false, "print version and exit")
	flag.Parse()

	if *showVersion {
		fmt.Println(version)
		return
	}

	inv, err := collector.Collect()
	if err != nil {
		fmt.Fprintln(os.Stderr, "collect:", err)
		os.Exit(1)
	}

	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")
	if err := enc.Encode(inv); err != nil {
		fmt.Fprintln(os.Stderr, "encode:", err)
		os.Exit(1)
	}
}
