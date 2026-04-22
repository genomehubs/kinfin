# Kinfin Development Container Setup

This directory contains the configuration for running Kinfin in a development container (devcontainer). A devcontainer provides a containerized development environment that isolates project dependencies and provides filesystem sandboxing.

## Quick Start

### Opening the Project in a Dev Container

1. **Install prerequisites:**
   - [Docker Desktop](https://www.docker.com/products/docker-desktop) (or equivalent container runtime)
   - [VS Code](https://code.visualstudio.com/) with the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

2. **Open in devcontainer:**
   - Open this project folder in VS Code
   - When prompted, click "Reopen in Container"
   - Alternatively, use the Command Palette: `Dev Containers: Reopen in Container`

3. **First run:**
   - VS Code will build the container and run `post-create.sh`
   - This installs Python and Node.js dependencies automatically
   - When complete, your environment is ready for development

### Running the Application

```bash
# Backend (FastAPI)
python -m src.main

# Frontend (React/Vite) - in another terminal
cd src/ui
npm run dev

# Run tests
python -m pytest tests/

# Frontend tests
cd src/ui && npm test

# Linting
cd src/ui && npm run lint
```

## What Gets Installed?

The devcontainer automatically installs:

- **Python 3.11** — primary development language
- **Node.js 20 LTS** — for React/Vite UI development
- **System dependencies** — build tools, SSL libraries, etc.
- **Python packages** — from `requirements.txt` and `requirements-dev.txt`
- **Node packages** — from `src/ui/package.json`
- **Project data** — databases via `install.sh`

## Sandboxing & AI Agent Safety

### Why Use This Devcontainer?

This devcontainer is designed with **AI agent safety** in mind:

1. **Filesystem Isolation**
   - Only `/workspace` (your project folder) is mounted into the container
   - The container cannot access your home directory (`~`) or `/Users`
   - System files are isolated — changes are confined to the container

2. **Process Isolation**
   - All code execution, scripts, and commands run inside the container
   - They cannot directly affect your host system or other projects
   - Package installations are isolated from your system Python/Node

3. **Network Context**
   - Network requests originate from the container context
   - Reduces risk of accidentally pulling from untrusted sources into your system

### Important Limitations

⚠️ **Devcontainers do NOT fully isolate VS Code extensions:**

- VS Code extensions (including Copilot Chat) partially run on the host OS
- They can theoretically access host files if given permission
- **Mitigation:** This is why we restrict mounts to `/workspace` only

### Sandboxing Guarantees

✅ **What is guaranteed:**

- No accidental writes to your home directory or system folders
- Project dependencies don't pollute your system Python/Node
- Scripts can't run arbitrary commands on your host system
- If something goes wrong in the container, delete and rebuild it

❌ **What is NOT guaranteed:**

- VS Code extensions have partial host access (configuration, settings)
- Copilot Chat can see your workspace settings and configuration
- A compromised extension could theoretically access host files
- Trust is still required in the tools and code being executed

### Best Practices for Safe AI Agent Use

1. **Always use the devcontainer** for Copilot Chat operations
   - Don't run agent requests on your host system
   - Close the container if you need to work on sensitive unrelated projects

2. **Review changes before committing**
   - Use `git diff` to audit what agents modified
   - Test changes locally before pushing
   - Never blindly commit agent output

3. **Restrict shell command execution**
   - Ask agents to print commands before executing them
   - Verify unfamiliar commands before confirming
   - VS Code settings restrict some unsafe operations

4. **Monitor what gets mounted**
   - Only `/workspace` should be visible in the container
   - Run `ls /home` inside the container — should show only `devuser`, not your home directory
   - If you need other directories, mount them explicitly and consider implications

5. **Use `.gitignore` appropriately**
   - Ensure sensitive files are excluded from the workspace
   - `.env` files and credentials should not be committed

## Advanced Configuration

### Using a Non-Root User

By default, the devcontainer runs as `devuser` (non-root). This adds a layer of sandboxing — processes cannot modify system files even if compromised.

**To run commands as root within container (if needed):**

```bash
sudo <command>
```

### Customizing the Environment

Edit the following files to customize your environment:

- **`Dockerfile`** — add system packages, change base image, modify user permissions
- **`devcontainer.json`** — configure VS Code, change ports, add features
- **`post-create.sh`** — run additional setup commands automatically

After changes, rebuild the container: `Dev Containers: Rebuild Container`

### Port Forwarding

The devcontainer forwards these ports by default:

- **3000** — Vite dev server (React UI)
- **8000** — FastAPI backend
- **6006** — Storybook documentation

Access these from your host via `localhost:PORT`.

### Mounting Additional Directories (Not Recommended)

If you need to mount additional directories, edit `devcontainer.json`:

```json
"mounts": [
  "source=${localWorkspaceFolder},target=/workspace,type=bind,consistency=consistent",
  "source=/path/to/data,target=/data,type=bind,readonly"  // Example: read-only mount
]
```

⚠️ **Caution:** Additional mounts weaken isolation. Mount only what's necessary and use `readonly` where possible.

## Troubleshooting

### Container won't build

1. **Check Docker:**

   ```bash
   docker --version
   docker ps
   ```

2. **Rebuild from scratch:**

   ```
   Dev Containers: Rebuild Container
   ```

   Or from terminal: `docker system prune -a`

3. **Check logs:**
   ```
   Dev Containers: Show Log
   ```

### Missing dependencies

If Python or Node packages are missing:

```bash
python -m pip install -r requirements.txt
pip install -r requirements-dev.txt
cd src/ui && npm install
```

### Can't access external files

The devcontainer intentionally restricts access outside `/workspace`. This is a security feature.

- Workaround: Copy files into `/workspace` (e.g., via mounted volume or copy commands)
- If you need persistent access, consider mounting (with `readonly` if possible)

### Port conflicts

If port 3000, 8000, or 6006 are already in use on your host:

1. Stop other services using those ports
2. Or edit `devcontainer.json` to use different ports
   ```json
   "portsAttributes": {
     "3000": { "label": "Vite Dev Server" }
   }
   ```

### Git operations inside container

Git should work normally inside the container. Your `.git` folder is part of `/workspace`.

```bash
git status
git log
git commit -m "message"
```

## Exiting the Dev Container

- **Switch to host machine:** Reopen the folder locally
  ```
  Dev Containers: Reopen Folder Locally
  ```
- **Keep multiple environments:** Open the same folder in a new VS Code window and toggle between host and container versions

## Additional Resources

- [VS Code Dev Containers Documentation](https://code.visualstudio.com/docs/devcontainers/containers)
- [Dev Container Specification](https://containers.dev/)
- [Docker Documentation](https://docs.docker.com/)

## Security Notes

This devcontainer is a practical security improvement, not military-grade isolation:

- For maximum safety with untrusted code, consider additional measures (read-only system, SELinux, AppArmor)
- Principle: defense in depth — layers of protection are better than a single mechanism
- Always review code before execution, regardless of sandboxing

---

**Questions?** See the main [README.md](../README.md) or open an issue on GitHub.
