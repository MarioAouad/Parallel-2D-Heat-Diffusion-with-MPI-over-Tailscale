# 0. Cluster setup: what each component does

This documents the setup already performed. It is not an instruction to reinstall working VMs.

| Component | Its job | What it does not do automatically |
| --- | --- | --- |
| Windows | Runs on each physical computer | Does not run the Linux MPI programs directly in this setup |
| VirtualBox | Provides each Ubuntu VM with virtual CPU, RAM, disk and networking | Does not turn one VM into several physical computers |
| Ubuntu Server 24.04 LTS | Provides a common Linux environment and package manager | Does not need a graphical desktop for this project |
| Tailscale inside Ubuntu | Connects the VMs using private overlay addresses | Does not install MPI or distribute source files |
| OpenSSH | Starts a remote shell and copies files | Does not itself implement the timed MPI payload exchange |
| Open MPI | Starts application ranks and implements their communication | Does not automatically split a grid or parallelize an ordinary loop |
| C++ compiler / make | Turn source into each VM's local executable | Do not run the experiment merely by building |
| Python / NumPy / Matplotlib | Analyze saved measurements and plot them | Do not create another measured run |

## The installation we performed

Each student created one Ubuntu Server VM. The intended minimum is two vCPUs and 4 GB RAM per VM, using NAT networking. heat-1's screenshot showed two vCPUs, 4096 MB and a 30 GB virtual disk. Record every VM's real allocation in [the inventory](../../docs/cluster-inventory.md).

At the end of Ubuntu installation, “failed unmounting cdrom” referred to the virtual installation ISO. Ejecting that virtual optical medium and continuing the reboot led to a normal Ubuntu login. It was not evidence that the subsequent Ubuntu installation failed.

The common project username is `mpi`. The third friend's original account was different; creating and using `mpi` fixed the mismatch. `mpi@host` means “log in to the Linux account mpi on host,” not “use a Tailscale account called mpi.”

## Two separate SSH routes

**Windows to your own VM:** our VirtualBox NAT forwarding rule maps host `127.0.0.1:2222` to guest port `22`.

```powershell
ssh -p 2222 mpi@127.0.0.1
```

`127.0.0.1` means the computer on which you type the command. Your friend's same command reaches their own VM, not yours. This forwarded route made copying/pasting easier using Windows Terminal. The VM console is a Linux text console; ordinary Windows clipboard shortcuts are not automatically available there.

**VM to another VM:** use the destination's Tailscale address and ordinary SSH port 22.

```bash
ssh mpi@HEAT2_TAILSCALE_IP hostname
```

Do not use `-p 2222` for this inter-VM connection. The repeated VirtualBox NAT address `10.0.2.15` is also not a usable destination for another student's VM.

## Tailscale setup we used

One team owner created the tailnet and invited both teammates. Each teammate joined with their own account and authorized Tailscale **inside their VM**. Users and machines are different: an invited user owns/enrolls one or more machines; the VM must appear as a machine too.

The installation/login pattern was:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --hostname=heat-1
tailscale status
tailscale ip -4
```

Use the VM's intended hostname when installing another node; preserve the third VM's actual name. The displayed authorization link is opened in a browser. Visiting the admin console alone does not authorize a logged-out VM. Password characters normally do not echo at a real Linux password prompt; never paste a password into the shell as a command.

A direct route links the peers without a Tailscale DERP relay. A relay route still permits encrypted communication but can add delay. A successful ping is not a guarantee of fast MPI bandwidth or passwordless SSH.

## Software and SSH service

The package command in the root README installs compiler tools, MPI, Python analysis packages, SSH and curl. `apt update` refreshes package indexes; `apt install` installs named packages. An “already newest version” message is normal. Check `mpirun --version` on every VM.

```bash
sudo systemctl enable --now ssh
```

This starts SSH now and enables it after reboots. Next read [the SSH/connectivity step](../01-connectivity/README.md). Keep existing working keys; do not regenerate them just to follow this explanation.
