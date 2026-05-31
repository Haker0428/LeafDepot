

## 本地开发

### 环境准备

- 安装 [Node.js](https://nodejs.org/en)
- 安装 [pnpm](https://pnpm.io/installation)

### 操作步骤

- 安装依赖

```sh
pnpm install
```

- 启动 Dev Server

```sh
pnpm run dev
```

- 启动 网关模块

```sh
sudo systemctl start leafdepot-gateway
```

- 启动 LMS服务端

```sh
sudo systemctl start leafdepot-lms
```

- 在浏览器访问 http://localhost:5173
