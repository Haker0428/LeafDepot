# 启动脚本

此目录包含所有服务的启动脚本。

## 脚本说明

- `start_gateway.sh` - 启动网关服务（端口 8000）
- `start_lms_sim.sh` - 启动 LMS 模拟服务（端口 6000）
- `start_rcs_sim.sh` - 启动 RCS 模拟服务（端口 4001）

## 使用方法

```bash
# 从项目根目录执行
./scripts/start_gateway.sh
./scripts/start_lms_sim.sh
./scripts/start_rcs_sim.sh
```

## 注意事项

- 确保已激活 Conda 环境：`conda activate tobacco_env`
- 确保已安装所有依赖
- 脚本会自动切换到正确的目录


