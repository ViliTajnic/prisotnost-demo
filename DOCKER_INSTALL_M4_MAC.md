# Docker Installation Guide for M4 MacBook

## 🚀 Quick Docker Installation

### Method 1: Homebrew Installation (Recommended)

```bash
# 1. Make sure Homebrew is installed first
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Add Homebrew to PATH for M4 Mac
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc
source ~/.zshrc

# 3. Install Docker Desktop via Homebrew
brew install --cask docker

# 4. Start Docker Desktop
open /Applications/Docker.app
```

### Method 2: Manual Download

1. **Go to**: [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)
2. **Click**: "Mac with Apple chip" (for M4 MacBook)
3. **Download**: Docker.dmg file
4. **Install**: Drag Docker to Applications folder
5. **Start**: Open Docker from Applications

## 🔧 Complete Setup Steps

### Step 1: Install Docker Desktop
```bash
# Install via Homebrew
brew install --cask docker

# Verify installation
ls -la /Applications/Docker.app
# Should show Docker.app directory
```

### Step 2: Start Docker Desktop
```bash
# Start Docker Desktop application
open /Applications/Docker.app

# Alternative: Start from Finder
# Applications → Docker → Double-click
```

### Step 3: Wait for Docker to Start
```bash
# Docker Desktop needs to start its services
# You'll see a Docker whale icon in your menu bar
#
# States:
# - Animated whale = Starting up
# - Solid whale = Ready to use
# - No whale = Not running

# This usually takes 30-60 seconds
```

### Step 4: Verify Docker Installation
```bash
# Check Docker version
docker --version
# Expected: Docker version 24.0.x, build...

# Check Docker Compose version
docker-compose --version
# Expected: Docker Compose version v2.x.x

# Test Docker with hello-world
docker run hello-world
# Should download and run successfully
```

## 🧪 Docker Installation Test

### Basic Test Commands
```bash
# 1. Check Docker daemon is running
docker info

# 2. List running containers (should be empty initially)
docker ps

# 3. Run test container
docker run --rm alpine echo "Docker works on M4 Mac!"

# 4. Check available images
docker images
```

### Expected Output
```bash
# docker --version
Docker version 24.0.7, build afdd53b

# docker run hello-world
Hello from Docker!
This message shows that your installation appears to be working correctly.
```

## 🔧 Docker Desktop Configuration

### Recommended Settings for M4 Mac
1. **Open Docker Desktop** from Applications
2. **Go to Settings** (gear icon)
3. **Configure Resources**:
   ```
   CPUs: 4-6 cores (out of 8-10 total)
   Memory: 8GB (out of 16GB+ total)
   Swap: 2GB
   Disk image size: 64GB
   ```

### Enable Kubernetes (Optional)
1. **Go to**: Settings → Kubernetes
2. **Check**: "Enable Kubernetes"
3. **Apply & Restart**

## 🚨 Troubleshooting Docker on M4 Mac

### Problem: Docker won't start
```bash
# Check if Docker Desktop is in Applications
ls /Applications/Docker.app

# Try restarting Docker
pkill -f Docker
open /Applications/Docker.app

# Check system resources
top -l 1 | grep -E "CPU|PhysMem"
```

### Problem: "docker: command not found"
```bash
# Add Docker to PATH manually
echo 'export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Verify
which docker
```

### Problem: Permission issues
```bash
# Docker Desktop usually handles this automatically
# But if needed, add user to docker group:
sudo dscl . append /Groups/_developer GroupMembership $(whoami)

# Restart terminal and Docker Desktop
```

### Problem: Slow performance
```bash
# Increase Docker Desktop resources:
# 1. Open Docker Desktop
# 2. Settings → Resources → Advanced
# 3. Increase CPUs to 6 and Memory to 12GB
# 4. Apply & Restart
```

## ⚡ Quick Docker Commands for Oracle Setup

### After Docker is Installed
```bash
# Pull Oracle 23ai Free image
docker pull container-registry.oracle.com/database/free:latest

# Create Oracle data directory
mkdir -p ~/oracle-data

# Run Oracle container (from the main setup guide)
docker run -d \
  --name oracle-23ai-free \
  -p 1521:1521 \
  -p 5500:5500 \
  -e ORACLE_PASSWORD=MyStrongPassword123 \
  -e ORACLE_CHARACTERSET=AL32UTF8 \
  -v ~/oracle-data:/opt/oracle/oradata \
  container-registry.oracle.com/database/free:latest

# Check Oracle container status
docker ps
docker logs oracle-23ai-free
```

## 📋 Docker Desktop Menu Bar Controls

When Docker is running, you'll see a whale icon in your menu bar:

- **Click the whale**: Access Docker Desktop dashboard
- **Preferences**: Configure Docker settings
- **Restart**: Restart Docker services
- **Quit Docker Desktop**: Stop all Docker services

## 🎯 Verification Checklist

- [ ] Docker Desktop installed successfully
- [ ] Docker whale icon appears in menu bar
- [ ] `docker --version` shows version 24.x.x
- [ ] `docker run hello-world` works without errors
- [ ] Docker Desktop dashboard opens
- [ ] Ready to run Oracle containers

## 🔄 Daily Docker Usage

### Starting Docker (if stopped)
```bash
# Start Docker Desktop
open /Applications/Docker.app

# Wait for whale icon in menu bar
# Check status
docker ps
```

### Stopping Docker (to save resources)
```bash
# Stop Docker Desktop via menu bar
# Click whale icon → "Quit Docker Desktop"

# Or via command line
osascript -e 'quit app "Docker Desktop"'
```

## 🚀 Next Steps

After Docker is installed and working:

1. **Return to main setup guide**: `COMPLETE_M4_MAC_SETUP.md`
2. **Continue with Part 2**: Database Setup
3. **Run Oracle 23ai Free container**
4. **Set up the Time Management application**

Docker is now ready for your Oracle database and application containers! 🐳