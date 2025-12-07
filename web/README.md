

## 本地开发

### 环境准备

- 安装 [Node.js](https://nodejs.org/en)
- 使用 npm（Node.js 自带）或 [pnpm](https://pnpm.io/installation)

### 操作步骤

#### 使用 npm（推荐）

- 安装依赖

```sh
npm install
```

- 启动 Dev Server

```sh
npm run dev
```

#### 使用 pnpm

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
cd /home/ubuntu/LeafDepot/Intergration/app
conda activate tobacco_env
bash start_gateway.sh
```

- 启动 LMS服务端

```sh
cd /home/ubuntu/LeafDepot/Intergration/app/sim/lms
conda activate tobacco_env
bash start_sim_lms_server.sh
```

- 在浏览器访问 http://localhost:3000
