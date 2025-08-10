# 软件许可证监控仪表板 (License Monitor Dashboard)

一个自动化的、基于Web的软件许可证使用情况监控仪表板，用于实时监控 FlexLM 许可证服务器的使用状态。

## 功能特性

### 🔄 自动化数据采集
- **定时执行**: 每5分钟自动执行 `lmstat.exe -c 29000@hqcndb -a` 命令
- **数据持久化**: 自动保存带时间戳的日志文件到 `backend/logs` 目录
- **调试模式**: 支持使用 `234.txt` 文件进行开发和测试

### 📊 实时数据监控
- **许可证状态**: 显示所有许可证特性的使用情况
- **用户信息**: 展示当前使用许可证的用户详情
- **使用率可视化**: 彩色进度条显示许可证使用率
- **系统状态**: 实时显示系统健康状态和最后更新时间

### 🔍 数据筛选与搜索
- **时间范围筛选**: 最新/本周/本月数据筛选
- **实时搜索**: 对许可证名称和用户名进行实时文本过滤
- **数据追溯**: 可查看历史日志文件

### 💻 现代化界面
- **响应式设计**: 支持桌面和移动设备
- **实时更新**: 自动刷新数据，无需手动操作
- **心电图可视化**: 系统健康状态的动态可视化
- **中英文双语**: 支持中文和英文界面

## 项目结构

```
LicStats/
├── 234.txt                 # 调试模式数据文件
├── README.md               # 项目说明文档
├── backend/                # 后端服务
│   ├── app.py             # Flask 主应用
│   ├── requirements.txt   # Python 依赖
│   └── logs/              # 日志存储目录
└── frontend/              # 前端界面
    └── index.html         # 主页面
```

## 安装和运行

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 启动后端服务

```bash
cd backend
python app.py
```

服务将在 `http://localhost:5000` 启动

### 3. 访问仪表板

打开浏览器访问: `http://localhost:5000`

## 配置说明

### app.py 配置项

```python
DEBUG_MODE = True           # 调试模式开关
LMSTAT_COMMAND = "lmstat.exe -c 29000@hqcndb -a"  # 许可证查询命令
UPDATE_INTERVAL = 5         # 数据采集间隔(分钟)
```

### 调试模式
- `DEBUG_MODE = True`: 使用 `234.txt` 文件作为数据源
- `DEBUG_MODE = False`: 执行实际的 `lmstat.exe` 命令

## API 端点

- `GET /api/status` - 获取系统状态
- `GET /api/health` - 获取健康状态数据
- `GET /api/licenses` - 获取最新许可证数据
- `GET /api/logs` - 获取日志文件列表
- `GET /api/logs/<filename>` - 获取特定日志文件内容
- `GET /api/collect` - 手动触发数据采集

## 技术栈

### 后端
- **Flask**: Python Web 框架
- **Flask-CORS**: 跨域资源共享
- **Schedule**: 定时任务调度
- **Subprocess**: 系统命令执行

### 前端
- **HTML5/CSS3**: 现代化界面设计
- **JavaScript (ES6+)**: 异步数据处理
- **Fetch API**: RESTful API 调用
- **CSS Grid/Flexbox**: 响应式布局

## 使用说明

### 1. 系统状态监控
- **在线状态**: 绿色指示器表示系统正常运行
- **最后更新时间**: 显示数据的最新采集时间
- **运行模式**: 显示当前是调试模式还是生产模式

### 2. 数据筛选
- **时间范围**: 选择要查看的数据时间范围
- **搜索过滤**: 实时搜索许可证特性或用户名
- **手动刷新**: 立即更新数据显示

### 3. 许可证信息
- **使用率**: 彩色进度条显示许可证使用情况
  - 绿色: 使用率 < 40%
  - 橙色: 使用率 40-70%
  - 红色: 使用率 > 70%
- **用户详情**: 展开显示当前使用许可证的用户信息

### 4. 健康监控
- **心电图**: 动态显示系统健康状态
- **统计信息**: 总许可证数和当前使用数

## 故障排除

### 常见问题

1. **无法连接到许可证服务器**
   - 检查网络连接
   - 确认许可证服务器地址和端口正确
   - 验证 `lmstat.exe` 命令可执行

2. **数据未更新**
   - 检查后端服务是否运行
   - 查看浏览器控制台错误信息
   - 手动点击"刷新数据"按钮

3. **界面显示异常**
   - 清除浏览器缓存
   - 检查网络连接
   - 确认浏览器支持现代Web标准

### 日志调试

- 后端服务日志: 查看控制台输出
- 数据采集日志: 检查 `backend/logs/` 目录下的文件
- 前端调试: 使用浏览器开发者工具

## 开发和扩展

### 添加新功能
1. 修改 `backend/app.py` 添加新的API端点
2. 更新 `frontend/index.html` 添加前端交互
3. 测试功能并更新文档

### 自定义配置
- 修改更新间隔: 调整 `UPDATE_INTERVAL` 变量
- 更改许可证服务器: 修改 `LMSTAT_COMMAND` 变量
- 自定义界面: 编辑 `index.html` 中的CSS样式

### 打包为EXE

可以使用 PyInstaller 将本应用打包为单个的可执行文件，方便在没有 Python 环境的 Windows 上运行。

1.  **安装 PyInstaller**:
    ```bash
    pip install pyinstaller
    ```

2.  **执行打包命令**:
    在项目根目录下运行以下命令：
    ```bash
    pyinstaller --onefile --name LicStats --add-data "frontend;frontend" backend/app.py
    ```
    *   `--onefile`: 创建单文件程序。
    *   `--name LicStats`: 指定输出的EXE文件名。
    *   `--add-data "frontend;frontend"`: 将前端文件打包进去。

3.  **找到可执行文件**:
    打包成功后，可在 `dist/` 目录下找到 `LicStats.exe` 文件。

## 许可证

本项目基于 MIT 许可证开source。