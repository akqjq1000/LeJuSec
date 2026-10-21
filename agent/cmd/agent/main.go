// Command agent is the LeJuSec target-system agent.
//
// Phase 1 skeleton: collects host inventory. Scanning, FIM, and signed
// transport are added per docs/roadmap.md.
package main

import (
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

	pkgs, err := collector.Packages()
	if err != nil {
		fmt.Fprintln(os.Stderr, "collect packages:", err)
		os.Exit(1)
	}
	fmt.Printf("lejusec-agent %s: collected %d packages\n", version, len(pkgs))
}
