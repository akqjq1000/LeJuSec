// Command agent is the LeJuSec target-system agent.
//
// Modes:
//   - default: collect host inventory (packages, processes)
//   - --scan:  run security scanners (Trivy/Lynis/OpenSCAP) and report findings
//
// Without --server the result is printed as JSON; with --server it is signed
// (Ed25519) and sent to the control plane, optionally over mutual TLS.
// --keygen creates an Ed25519 keypair for registration.
package main

import (
	"crypto/tls"
	"encoding/json"
	"flag"
	"fmt"
	"os"

	"github.com/akqjq1000/LeJuSec/agent/internal/client"
	"github.com/akqjq1000/LeJuSec/agent/internal/collector"
	"github.com/akqjq1000/LeJuSec/agent/internal/scan"
	"github.com/akqjq1000/LeJuSec/agent/internal/signing"
)

// version is injected at build time via -ldflags "-X main.version=...".
var version = "dev"

type options struct {
	server     string
	assetID    int
	keyPath    string
	caCert     string
	clientCert string
	clientKey  string
	scanMode   bool
	scanCfg    scan.Config
}

func main() {
	showVersion := flag.Bool("version", false, "print version and exit")
	keygen := flag.String("keygen", "", "generate an Ed25519 keypair, write the private key to this path, print the public key")
	opts := options{}
	flag.StringVar(&opts.keyPath, "key", "", "path to the Ed25519 private key (used with --server)")
	flag.StringVar(&opts.server, "server", "", "control-plane base URL (e.g. https://host:8000)")
	flag.IntVar(&opts.assetID, "asset-id", 0, "asset id to report for (used with --server)")
	flag.StringVar(&opts.caCert, "ca-cert", "", "CA certificate to verify the control plane (enables mTLS)")
	flag.StringVar(&opts.clientCert, "client-cert", "", "client certificate for mTLS")
	flag.StringVar(&opts.clientKey, "client-key", "", "client private key for mTLS")
	flag.BoolVar(&opts.scanMode, "scan", false, "run scanners and report findings instead of inventory")
	flag.StringVar(&opts.scanCfg.TrivyPath, "scan-path", "", "filesystem path for `trivy fs` (empty to skip)")
	flag.StringVar(&opts.scanCfg.LynisReport, "lynis-report", "", "path to a lynis report .dat (empty to skip)")
	flag.StringVar(&opts.scanCfg.OpenSCAPResults, "oscap-results", "", "path to OpenSCAP XCCDF results XML (empty to skip)")
	flag.Parse()

	switch {
	case *showVersion:
		fmt.Println(version)
		return
	case *keygen != "":
		if err := doKeygen(*keygen); err != nil {
			fail(err)
		}
		return
	}

	if err := run(opts); err != nil {
		fail(err)
	}
}

func run(opts options) error {
	// 로컬 출력 모드 (--server 미지정): 결과를 JSON으로 출력
	if opts.server == "" {
		if opts.scanMode {
			findings, err := scan.Collect(opts.scanCfg)
			if err != nil {
				return err
			}
			return printJSON(findings)
		}
		inv, err := collector.Collect()
		if err != nil {
			return err
		}
		return printJSON(inv)
	}

	if opts.keyPath == "" || opts.assetID == 0 {
		return fmt.Errorf("--server requires --key and --asset-id")
	}
	priv, err := signing.LoadPrivateKey(opts.keyPath)
	if err != nil {
		return err
	}
	tlsConf, err := buildTLS(opts.caCert, opts.clientCert, opts.clientKey)
	if err != nil {
		return err
	}
	api := client.New(opts.server, tlsConf)

	if opts.scanMode {
		findings, err := scan.Collect(opts.scanCfg)
		if err != nil {
			return err
		}
		if err := api.SendScan(opts.assetID, priv, findings); err != nil {
			return err
		}
		fmt.Printf("sent scan: %d findings\n", len(findings))
		return nil
	}

	inv, err := collector.Collect()
	if err != nil {
		return err
	}
	if err := api.SendInventory(opts.assetID, priv, inv); err != nil {
		return err
	}
	fmt.Printf("sent inventory: %d packages, %d processes\n", len(inv.Packages), len(inv.Processes))
	return nil
}

// buildTLS returns a mutual-TLS config when the three cert flags are set, nil
// when none are set, or an error when they are set inconsistently.
func buildTLS(caCert, clientCert, clientKey string) (*tls.Config, error) {
	if caCert == "" && clientCert == "" && clientKey == "" {
		return nil, nil
	}
	if caCert == "" || clientCert == "" || clientKey == "" {
		return nil, fmt.Errorf("--ca-cert, --client-cert and --client-key must be set together")
	}
	return client.BuildTLSConfig(client.TLSPaths{
		ClientCert: clientCert,
		ClientKey:  clientKey,
		CACert:     caCert,
	})
}

func doKeygen(path string) error {
	privB64, pubB64, err := signing.GenerateKey()
	if err != nil {
		return err
	}
	if err := os.WriteFile(path, []byte(privB64+"\n"), 0o600); err != nil {
		return err
	}
	fmt.Printf("private key written to %s\n", path)
	fmt.Printf("public key (register via PUT /assets/{id}/key):\n%s\n", pubB64)
	return nil
}

func printJSON(value any) error {
	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")
	return enc.Encode(value)
}

func fail(err error) {
	fmt.Fprintln(os.Stderr, "agent:", err)
	os.Exit(1)
}
