# Private team configuration and public examples

The public repository uses generic node labels heat-1, heat-2, heat-3. Actual hostnames and network addresses are retained in the team's private originals. Configure only when ready to run the organized checkout; reading results needs no configuration.

On each VM, from the repository root:

```bash
cp part0/config/cluster.local.sh.example part0/config/cluster.local.sh
nano part0/config/cluster.local.sh
```

Replace the three quoted placeholders with the real Tailscale IPv4 addresses, obtained with `tailscale ip -4` in each VM. Use the same VM order on every checkout. Save the actual configuration locally; `.gitignore` excludes it. No passwords or authentication keys belong in this file.

The launchers source `cluster.sh`, which validates local values and renders the ignored `hosts` file with two slots per VM. `hosts.example` shows the required syntax with placeholders. You do not type the addresses twice. Missing or placeholder configuration produces an explanation instead of launching MPI with invalid endpoints.

Hostname/hello use the rendered six-slot hostfile. Ping-pong chooses exactly two slots from the same configuration: two on one VM or one on each pair endpoint. Changing slot numbers does not allocate extra vCPUs.

Keep local configuration and original private route/metadata files out of the public repository. Preserve archived public measurements; separately record every new run and its private configuration.
