// Command agent is the LeJuSec target-system agent.
//
// Phase 1: collects a host inventory (packages, processes). Without --server it
// prints the inventory as JSON; with --server it signs and sends it to the
// control plane, optionally over mutual TLS. --keygen creates an Ed25519
// keypair for registration.
package main

import (
	"crypto/tls"
	"encoding/json"
	"flag"
	"fmt"
	"os"

	"github.com/akqjq1000/LeJuSec/agent/internal/client"
	"github.com/akqjq1000/LeJuSec/agent/internal/collector"
	"github.com/akqjq1000/LeJuSec/agent/internal/signing"
)

// version is injected at build time via -ldflags "-X main.version=...".
var version = "dev"

func main() {
	showVersion := flag.Bool("version", false, "print version and exit")
	keygen := flag.String("keygen", "", "generate an Ed25519 keypair, write the private key to this path, print the public key")
	keyPath := flag.String("key", "", "path to the Ed25519 private key (used with --server)")
	server := flag.String("server", "", "control-plane base URL to send inventory to (e.g. https://host:8000)")
	assetID := flag.Int("asset-id", 0, "asset id to report inventory for (used with --server)")
	caCert := flag.String("ca-cert", "", "CA certificate to verify the control plane (enables mTLS)")
	clientCert := flag.String("client-cert", "", "client certificate for mTLS")
	clientKey := flag.String("client-key", "", "client private key for mTLS")
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

	inv, err := collector.Collect()
	if err != nil {
		fail(err)
	}

	if *server == "" {
		printJSON(inv)
		return
	}

	if *keyPath == "" || *assetID == 0 {
		fail(fmt.Errorf("--server requires --key and --asset-id"))
	}
	priv, err := signing.LoadPrivateKey(*keyPath)
	if err != nil {
		fail(err)
	}

	tlsConf, err := buildTLS(*caCert, *clientCert, *clientKey)
	if err != nil {
		fail(err)
	}

	if err := client.New(*server, tlsConf).SendInventory(*assetID, priv, inv); err != nil {
		fail(err)
	}
	fmt.Printf("sent inventory: %d packages, %d processes\n", len(inv.Packages), len(inv.Processes))
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

func printJSON(inv collector.Inventory) {
	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")
	if err := enc.Encode(inv); err != nil {
		fail(err)
	}
}

func fail(err error) {
	fmt.Fprintln(os.Stderr, "agent:", err)
	os.Exit(1)
}
