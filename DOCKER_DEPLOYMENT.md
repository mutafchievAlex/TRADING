# Docker Deployment Guide

## Overview
This trading system can be deployed in Docker containers for reliable, isolated execution that continues even when the host machine goes to sleep or reboots.

## Prerequisites
- Docker (v20.10+)
- Docker Compose (v1.29+)
- 2GB RAM minimum per container
- 500MB disk space for state/data

## Quick Start

### 1. Build the image (one-time)
```bash
chmod +x docker-manage.sh
./docker-manage.sh build
```

### 2. Start trading system (production)
```bash
./docker-manage.sh start
```

The system will:
- Run in background
- Auto-restart if container crashes
- Auto-start after host reboot
- Persist state in `./data/` volume

### 3. Monitor in real-time
```bash
./docker-manage.sh logs
```

### 4. Check health
```bash
./docker-manage.sh health
```

## Detailed Commands

### Production Deployment
```bash
# Build image
./docker-manage.sh build

# Start in background (auto-restart on failure)
./docker-manage.sh start

# View logs
./docker-manage.sh logs

# Check if healthy
./docker-manage.sh health

# Graceful stop
./docker-manage.sh stop

# Restart if needed
./docker-manage.sh restart
```

### Development with UI
```bash
# Start with graphical interface (blocking, shows all output)
./docker-manage.sh dev

# In separate terminal, access shell
./docker-manage.sh shell
```

### Manual Docker Compose
```bash
# Production
docker-compose -f docker-compose.yml up -d

# Development with UI
docker-compose -f docker-compose.dev.yml up

# View logs
docker-compose logs -f --tail=100

# Stop all
docker-compose down
```

## Configuration

### Environment Variables
Edit `docker-compose.yml` to modify:
- `TRADING_MODE`: Set to `PRODUCTION` for live trading, `DEVELOPMENT` for safe testing
- `TRADING_CONFIG`: Path to config file (default: `/app/config/config.yaml`)
- `TZ`: Timezone (default: UTC)

### Resource Limits
The container is configured with:
- **CPU limit**: 2 cores (can use up to 2, typically uses 0.2-0.5)
- **Memory limit**: 2GB (typical usage 300-500MB)
- **CPU reservation**: 1 core minimum
- **Memory reservation**: 1GB minimum

Adjust in `docker-compose.yml` if needed:
```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
```

## Volume Mounts

### Data Persistence
- `./data/` - Trade history, state, backups
- `./logs/` - Application logs
- `./reports/` - Backtest reports
- `./config/` - Configuration files (read-only in prod)

### Adding Custom Configuration
```bash
# Edit config file on host
vim config/config.yaml

# Changes are reflected in container immediately (no restart needed)
```

## Restart Behavior

### Auto-Restart Policy
The container has `restart: always` which means:
1. Container auto-restarts if it crashes
2. Container auto-starts after Docker daemon restart
3. Container auto-starts after host reboot

### Graceful Shutdown
```bash
# Stop trading gracefully (flush pending trades)
./docker-manage.sh stop

# This gives the system 30 seconds to clean up before force-killing
# Check logs to verify graceful shutdown
./docker-manage.sh logs
```

## Monitoring

### Real-time Logs
```bash
./docker-manage.sh logs        # Last 50 lines with follow

# Or with Docker Compose directly
docker-compose logs -f --tail=100
```

### Container Status
```bash
./docker-manage.sh health

# Or
docker-compose ps
```

### System Metrics
```bash
# CPU and memory usage
docker stats trading_system_xauusd

# Detailed inspection
docker inspect trading_system_xauusd
```

## Troubleshooting

### Container exits immediately
```bash
# Check logs
./docker-manage.sh logs

# Enter shell to debug
./docker-manage.sh shell

# Verify config exists
ls -la /app/config/
```

### Connection issues
```bash
# Check MT5 connection inside container
./docker-manage.sh shell
python -c "from src.engines.market_data_service import MarketDataService; m = MarketDataService(); print(m.connect())"
```

### Resource exhaustion
```bash
# Check memory usage
docker stats

# Increase limits in docker-compose.yml
# Restart
./docker-manage.sh restart
```

### Data not persisting
```bash
# Verify volume mount
docker-compose exec trading-bot ls -la /app/data/

# Check host directory exists
ls -la ./data/
```

## Security Considerations

### Secrets Management
**Never** store credentials in docker-compose.yml. Instead:
1. Create `.env` file (add to `.gitignore`)
2. Use `${VARIABLE}` syntax in compose file
3. Docker Compose loads `.env` automatically

Example `.env`:
```
MT5_LOGIN=12345678
MT5_PASSWORD=secretpassword
MT5_SERVER=HotForexDemand
```

### Network Isolation
- Container runs on internal `trading_network`
- No external port exposure by default
- All data stored in mounted volumes on host

## Performance

### Typical Resource Usage
- **CPU**: 0.2-0.5 cores (1% of 2-core limit)
- **Memory**: 300-500MB (15-25% of 2GB limit)
- **Disk**: 50-100MB for logs per month
- **Network**: 1-2 Mbps average

### Optimization Tips
1. Set correct timeframe in config (1H minimum for stable runs)
2. Use `bars_to_fetch: 500` for sufficient history
3. Set `ui.continuous_update_interval_seconds: 5` for responsive UI
4. Adjust `ui.refresh_interval_seconds` based on your needs

## Updating Application

### Pull latest code
```bash
git pull origin main

# Rebuild image
./docker-manage.sh build

# Stop old container
./docker-manage.sh stop

# Start new container
./docker-manage.sh start
```

### Zero-downtime updates
```bash
# Edit code/config on host
vim src/main.py  # or config file

# Changes in mounted volumes reflect immediately
# No container restart needed for config changes
# Restart only if changing dependencies
```

## Logs

### Log Locations
- **Host**: `./logs/trading_system.log`
- **Container**: `/app/logs/trading_system.log`
- **Docker**: `./logs/` (docker-compose logs)

### Log Rotation
Configured to:
- Keep max 100MB per file
- Keep max 10 historical files
- Auto-compress old files

## Backup

### Regular backups
```bash
# Backup state and history
tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz ./data/

# Restore from backup
tar -xzf backup_20240115_120000.tar.gz
./docker-manage.sh restart
```

## Production Checklist

- [ ] Dockerfile built successfully
- [ ] docker-compose.yml reviewed and updated with secrets
- [ ] Volume mounts created and accessible
- [ ] Resource limits appropriate for host
- [ ] Logs being collected
- [ ] Health checks passing
- [ ] Test start/stop/restart cycle
- [ ] Test host reboot auto-start
- [ ] Backup strategy implemented
- [ ] Monitoring/alerting configured (external)
- [ ] Database connection working
- [ ] MT5 credentials secure
- [ ] Config files validated

## Next Steps

1. **Deploy**: `./docker-manage.sh start`
2. **Monitor**: `./docker-manage.sh logs` (in separate terminal)
3. **Verify**: `./docker-manage.sh health` (every 5 min initially)
4. **Backup**: Set up daily backup of `./data/` directory

## Support

For issues, check:
1. Container logs: `./docker-manage.sh logs`
2. Host disk space: `df -h`
3. Docker daemon health: `docker ps`
4. Network connectivity: `docker network inspect trading_network`
