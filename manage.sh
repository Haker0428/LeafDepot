#!/bin/bash
###
# 服务管理脚本
# 用法:
#   ./manage.sh start gateway   # 启动gateway服务
#   ./manage.sh start lms       # 启动lms服务
#   ./manage.sh start web       # 启动web服务
#   ./manage.sh start all       # 启动所有服务
#   ./manage.sh end gateway     # 停止gateway服务
#   ./manage.sh end lms         # 停止lms服务
#   ./manage.sh end web          # 停止web服务
#   ./manage.sh end all          # 停止所有服务
#   ./manage.sh status           # 查看所有服务状态
###

# 获取脚本所在目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
PID_DIR="$PROJECT_ROOT/.pids"
mkdir -p "$PID_DIR"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# 获取PID文件路径
get_pid_file() {
    local service=$1
    echo "$PID_DIR/${service}.pid"
}

# 检查进程是否运行
is_running() {
    local pid=$1
    if [ -z "$pid" ]; then
        return 1
    fi
    kill -0 "$pid" 2>/dev/null
}

# 启动gateway服务
start_gateway() {
    local pid_file=$(get_pid_file "gateway")
    
    # 检查是否已经运行
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if is_running "$pid"; then
            log_warn "Gateway服务已经在运行 (PID: $pid)"
            return 1
        else
            rm -f "$pid_file"
        fi
    fi
    
    log_info "启动Gateway服务..."
    
    # 设置PYTHONPATH
    export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
    
    # 切换到服务目录并在后台启动
    cd "$PROJECT_ROOT/services/api"
    nohup uvicorn gateway:app --host 0.0.0.0 --port 8000 --reload > "$PROJECT_ROOT/logs/gateway.log" 2>&1 &
    local pid=$!
    
    # 保存PID
    echo $pid > "$pid_file"
    
    sleep 2
    if is_running "$pid"; then
        log_info "Gateway服务启动成功 (PID: $pid)"
        log_info "日志文件: $PROJECT_ROOT/logs/gateway.log"
        log_info "API文档: http://localhost:8000/docs"
    else
        log_error "Gateway服务启动失败"
        rm -f "$pid_file"
        return 1
    fi
}

# 启动lms服务
start_lms() {
    local pid_file=$(get_pid_file "lms")
    
    # 检查是否已经运行
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if is_running "$pid"; then
            log_warn "LMS服务已经在运行 (PID: $pid)"
            return 1
        else
            rm -f "$pid_file"
        fi
    fi
    
    log_info "启动LMS服务..."
    
    # 设置PYTHONPATH
    export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
    
    # 切换到服务目录并在后台启动
    cd "$PROJECT_ROOT/services/sim/lms"
    nohup uvicorn sim_lms_server:app --host 0.0.0.0 --port 6000 --reload > "$PROJECT_ROOT/logs/lms.log" 2>&1 &
    local pid=$!
    
    # 保存PID
    echo $pid > "$pid_file"
    
    sleep 2
    if is_running "$pid"; then
        log_info "LMS服务启动成功 (PID: $pid)"
        log_info "日志文件: $PROJECT_ROOT/logs/lms.log"
        log_info "服务地址: http://localhost:6000"
    else
        log_error "LMS服务启动失败"
        rm -f "$pid_file"
        return 1
    fi
}

# 启动web服务
start_web() {
    local pid_file=$(get_pid_file "web")
    
    # 检查是否已经运行
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if is_running "$pid"; then
            log_warn "Web服务已经在运行 (PID: $pid)"
            return 1
        else
            rm -f "$pid_file"
        fi
    fi
    
    log_info "启动Web服务..."
    
    # 切换到web目录并在后台启动
    cd "$PROJECT_ROOT/web"
    nohup npm run dev > "$PROJECT_ROOT/logs/web.log" 2>&1 &
    local pid=$!
    
    # 保存PID
    echo $pid > "$pid_file"
    
    sleep 3
    if is_running "$pid"; then
        log_info "Web服务启动成功 (PID: $pid)"
        log_info "日志文件: $PROJECT_ROOT/logs/web.log"
        log_info "访问地址: http://localhost:3000"
    else
        log_error "Web服务启动失败"
        rm -f "$pid_file"
        return 1
    fi
}

# 停止服务
stop_service() {
    local service=$1
    local pid_file=$(get_pid_file "$service")
    
    if [ ! -f "$pid_file" ]; then
        log_warn "$service 服务未运行（PID文件不存在）"
        return 1
    fi
    
    local pid=$(cat "$pid_file")
    
    if ! is_running "$pid"; then
        log_warn "$service 服务未运行 (PID: $pid)"
        rm -f "$pid_file"
        return 1
    fi
    
    log_info "停止 $service 服务 (PID: $pid)..."
    
    # 杀死进程及其子进程
    kill -TERM "$pid" 2>/dev/null
    
    # 等待进程结束
    local count=0
    while is_running "$pid" && [ $count -lt 10 ]; do
        sleep 1
        count=$((count + 1))
    done
    
    # 如果还在运行，强制杀死
    if is_running "$pid"; then
        log_warn "进程未正常退出，强制杀死..."
        kill -KILL "$pid" 2>/dev/null
        sleep 1
    fi
    
    if ! is_running "$pid"; then
        log_info "$service 服务已停止"
        rm -f "$pid_file"
    else
        log_error "$service 服务停止失败"
        return 1
    fi
}

# 查看服务状态
show_status() {
    echo ""
    echo "=== 服务状态 ==="
    echo ""
    
    local services=("gateway" "lms" "web")
    local all_stopped=true
    
    for service in "${services[@]}"; do
        local pid_file=$(get_pid_file "$service")
        if [ -f "$pid_file" ]; then
            local pid=$(cat "$pid_file")
            if is_running "$pid"; then
                echo -e "${GREEN}✓${NC} $service: 运行中 (PID: $pid)"
                all_stopped=false
            else
                echo -e "${RED}✗${NC} $service: 已停止 (PID文件存在但进程不存在)"
                rm -f "$pid_file"
            fi
        else
            echo -e "${RED}✗${NC} $service: 未运行"
        fi
    done
    
    echo ""
    if [ "$all_stopped" = true ]; then
        log_info "所有服务都已停止"
    fi
}

# 主函数
main() {
    local command=$1
    local service=$2
    
    # 创建日志目录
    mkdir -p "$PROJECT_ROOT/logs"
    
    case "$command" in
        start)
            if [ "$service" = "all" ]; then
                log_info "启动所有服务..."
                start_gateway
                sleep 1
                start_lms
                sleep 1
                start_web
                echo ""
                show_status
            else
                case "$service" in
                    gateway)
                        start_gateway
                        ;;
                    lms)
                        start_lms
                        ;;
                    web)
                        start_web
                        ;;
                    *)
                        log_error "未知的服务: $service"
                        echo "用法: $0 start [gateway|lms|web|all]"
                        exit 1
                        ;;
                esac
            fi
            ;;
        end|stop)
            if [ "$service" = "all" ]; then
                log_info "停止所有服务..."
                stop_service "gateway"
                stop_service "lms"
                stop_service "web"
            else
                case "$service" in
                    gateway|lms|web)
                        stop_service "$service"
                        ;;
                    *)
                        log_error "未知的服务: $service"
                        echo "用法: $0 end [gateway|lms|web|all]"
                        exit 1
                        ;;
                esac
            fi
            ;;
        status)
            show_status
            ;;
        *)
            echo "用法: $0 {start|end|status} [gateway|lms|web|all]"
            echo ""
            echo "命令:"
            echo "  start <service>  启动指定服务（或使用 'all' 启动所有服务）"
            echo "  end <service>    停止指定服务（或使用 'all' 停止所有服务）"
            echo "  status           查看所有服务状态"
            echo ""
            echo "服务:"
            echo "  gateway          Gateway API服务 (端口 8000)"
            echo "  lms              LMS模拟服务 (端口 6000)"
            echo "  web              Web前端服务 (端口 3000)"
            echo "  all              所有服务"
            echo ""
            echo "示例:"
            echo "  $0 start gateway      # 启动gateway服务"
            echo "  $0 start lms          # 启动lms服务"
            echo "  $0 start web          # 启动web服务"
            echo "  $0 start all          # 启动所有服务"
            echo "  $0 end gateway        # 停止gateway服务"
            echo "  $0 end all            # 停止所有服务"
            echo "  $0 status             # 查看服务状态"
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"

