<template>
	<frame>
		<div class="ssh-container">
			<div class="left-panel">
				<el-card class="box-card" :body-style="{ padding: '10px', height: '100%' }">
					<template #header>
						<div class="card-header">
							<span>服务器列表</span>
							<el-input v-model="search" size="small" placeholder="按IP搜索"
								style="width: 120px; margin-left: 10px;" />
						</div>
					</template>

					<el-table :data="filterTableData" style="width: 100%" size="small" highlight-current-row
						@row-click="handleRowClick" height="calc(100vh - 180px)">
						<el-table-column label="主机名" prop="hostname" show-overflow-tooltip min-width="100" />
						<el-table-column label="IP" prop="ip" width="120" />

						<el-table-column fixed="right" label="操作" width="60">
							<template #default="scope">
								<el-button link type="primary" size="small"
									@click.stop="connect(scope.row.ip)">连接</el-button>
							</template>
						</el-table-column>
					</el-table>
				</el-card>
			</div>

			<div class="right-panel">
				<div class="term-header">
					<div v-if="currentConnection.ip" class="connection-info">
						<span class="label">当前连接:</span>
						<span class="value">{{ currentConnection.user }}@{{ currentConnection.ip }}</span>
						<el-tag type="success" size="small" effect="dark" style="margin-left: 10px;">SSH</el-tag>
					</div>
					<div v-else class="connection-info">
						<span class="label">未连接</span>
					</div>

					<el-button v-if="currentConnection.ip" type="danger" size="small"
						@click="disconnectSSH">断开连接</el-button>
				</div>

				<div class="term-body">
					<div id="xterm" class="xterm-container"></div>
					<div v-if="!currentConnection.ip" class="placeholder-text">
						<el-empty description="请从左侧列表选择服务器进行连接" />
					</div>
				</div>
			</div>
		</div>

		<el-dialog v-model="dialogFormVisible" title="连接鉴权" width="400px" draggable append-to-body>
			<el-form :model="connectData" :rules="rules" ref='formTag' label-position="top">
				<el-form-item label="用户名" prop="user">
					<el-input v-model="connectData.user" autocomplete="off" placeholder="root" />
				</el-form-item>
				<el-form-item label="密码" prop="password">
					<el-input v-model="connectData.password" type="password" show-password autocomplete="off"
						@keyup.enter="onsubmit" />
				</el-form-item>
			</el-form>
			<template #footer>
				<div class="dialog-footer">
					<el-button @click="dialogFormVisible = false">取消</el-button>
					<el-button type="primary" @click="onsubmit" :loading="isloading">
						立即连接
					</el-button>
				</div>
			</template>
		</el-dialog>
	</frame>
</template>

<script setup>
	import frame from "@/views/main/frame.vue";
	import authHttp from "@/api/authHttp";
	import websshHttp from "@/api/websshHttp";
	import {
		onMounted,
		onBeforeUnmount,
		ref,
		computed,
		reactive,
		nextTick
	} from "vue";
	import {
		ElMessage
	} from "element-plus";
	import 'xterm/css/xterm.css';
	import {
		Terminal
	} from 'xterm';
	import {
		FitAddon
	} from 'xterm-addon-fit';
	import clusterHttp from "@/api/clusterHttp";

	// --- 数据定义 ---
	// 1. 左侧列表相关
	const tableData = ref([]);
	const search = ref("");
	const dialogFormVisible = ref(false);
	const isloading = ref(false);
	let server_ip = ref(''); // 暂存点击的IP

	// 2. 终端相关
	const socket = ref(null);
	const term = ref(null);
	const fitAddon = ref(null);
	// 记录当前连接状态，用于 UI 显示
	const currentConnection = reactive({
		ip: '',
		user: '',
		password: ''
	});

	// 3. 表单相关
	let connectData = reactive({
		user: 'root',
		password: ''
	}); // 默认给个root方便
	let rules = reactive({
		user: [{
			required: true,
			message: '必填',
			trigger: 'blur'
		}],
		password: [{
			required: true,
			message: '必填',
			trigger: 'blur'
		}]
	});
	const formTag = ref(null);

	// --- 生命周期与初始化 ---
	onMounted(async () => {
		try {
			// 1. 并行请求数据
			const [result_idc, result_node] = await Promise.all([
				authHttp.getIdcServer(),
				clusterHttp.getClusterNodes()
			]);

			// --- 调试日志 (建议保留，方便排查) ---
			console.log("IDC数据:", result_idc);
			console.log("Node数据:", result_node);

			// 2. 处理 IDC 数据 (假设 result_idc 是直接的数组)
			// 如果 IDC 接口也开启了分页，请检查是否需要改为 result_idc.results
			const idcData = Array.isArray(result_idc) ? result_idc : (result_idc.results || []);

			const idcList = idcData.map(item => ({
				id: `idc-${item.id}`,
				hostname: item.hostname,
				ip: item.ip,
				region: item.region,
				scan_status: item.scan_status,
				type: 'IDC'
			}));

			// 3. 处理 Node 数据 (重点修复：兼容分页结构)
			// 判断 result_node 是否包含 .results 属性 (DRF 标准分页)
			let nodeData = [];
			if (Array.isArray(result_node)) {
				nodeData = result_node;
			} else if (result_node && result_node.results) {
				nodeData = result_node.results; // 取出真正的数组
			}

			const nodeList = nodeData.map(item => ({
				id: `node-${item.id}`,
				hostname: item.name, // 如果 Node 没有 hostname，可以用 item.name 
				ip: item.ip_address, // <--- 映射 ip_address 到 ip
				region: 'Kubernetes', // 默认值
				scan_status: 2, // 默认正常
				type: 'Cluster'
			}));

			// 4. 合并并赋值
			tableData.value = [...idcList, ...nodeList];

		} catch (error) {
			console.error("初始化数据失败:", error);
			ElMessage.error("获取服务器列表失败");
		}

		window.addEventListener('resize', handleResize);
	});

	onBeforeUnmount(() => {
		disconnectSSH(); // 组件销毁时断开连接
		window.removeEventListener('resize', handleResize);
	});

	// --- 左侧逻辑 ---
	const filterTableData = computed(() =>
		tableData.value.filter(
			(data) => !search.value || data.ip.toLowerCase().includes(search.value.toLowerCase())
		)
	);

	// 状态小圆点样式辅助函数
	const getStatusClass = (status) => {
		if (status === 0) return 'status-error'; // 异常
		if (status === 1) return 'status-fault'; // 故障
		if (status === 2) return 'status-normal'; // 正常
		return 'status-unknown';
	}

	// 点击表格行
	const handleRowClick = (row) => {
		// 可以在这里做预选中的逻辑，或者直接触发连接弹窗
		// 目前保留点击“连接”按钮触发
	};

	// 点击连接按钮
	const connect = (ip) => {
		server_ip.value = ip;
		connectData.password = ''; // 清空密码
		// connectData.user = 'root'; // 可以保留上次的用户名
		dialogFormVisible.value = true;
	};

	// 提交连接表单
	const onsubmit = async () => {
		if (!formTag.value) return;
		await formTag.value.validate(async (valid) => {
			if (valid) {
				try {
					isloading.value = true;
					// 1. 先验证连接 (可选，如果后端 websocket 也会验证，这一步可以跳过以加快速度)
					await websshHttp.checkConnect(connectData.user, server_ip.value, connectData
						.password);

					// 2. 验证成功，关闭弹窗
					dialogFormVisible.value = false;
					isloading.value = false;

					// 3. 触发右侧终端连接
					startSSHConnection(server_ip.value, connectData.user, connectData.password);

				} catch (detail) {
					isloading.value = false;
					ElMessage.error(typeof detail === 'string' ? detail : '连接验证失败');
				}
			}
		});
	};

	// --- 右侧 Xterm 核心逻辑 ---

	// 断开旧连接（清理资源）
	const disconnectSSH = () => {
		if (socket.value) {
			socket.value.close();
			socket.value = null;
		}
		if (term.value) {
			term.value.dispose(); // 销毁实例
			term.value = null;
		}
		// 重置状态
		currentConnection.ip = '';
		currentConnection.user = '';
	};

	// 启动新连接
	const startSSHConnection = (ip, user, password) => {
		// 1. 如果已有连接，先断开
		disconnectSSH();

		// 2. 更新当前连接状态
		currentConnection.ip = ip;
		currentConnection.user = user;
		currentConnection.password = password;

		// 3. 必须在 nextTick 后初始化，确保 DOM 元素 #xterm 存在（因为用了 v-if 控制 placeholder）
		nextTick(() => {
			initTerm(); // 初始化 xterm 界面
			initSocket(); // 初始化 websocket
		});
	};

	// 初始化 Xterm
	const initTerm = () => {
		const termContainer = document.getElementById('xterm');
		if (!termContainer) return;

		const newTerm = new Terminal({
			fontFamily: '"Cascadia Code", "Menlo", "Consolas", monospace',
			fontSize: 14, // 稍微调小一点适应布局
			cursorBlink: true,
			rendererType: "canvas",
			rows: 40,
			cols: 100,
			convertEol: true, // 重要
			disableStdin: false,
			windowsMode: true,
			cursorStyle: "underline",
			scrollback: 5000,
			theme: {
				foreground: "#ECECEC",
				background: "#1e1e1e", // 更深的黑色背景
				cursor: "help",
			},
		});

		const fit = new FitAddon();
		fitAddon.value = fit;
		newTerm.loadAddon(fit);

		newTerm.open(termContainer);
		fit.fit(); // 第一次自适应
		newTerm.focus();

		term.value = newTerm;

		// 监听输入发送给 Socket
		newTerm.onData((val) => {
			if (socket.value && socket.value.readyState === 1) {
				socket.value.send(JSON.stringify({
					'command': val
				}));
			}
		});
	};

	// 初始化 WebSocket
	const initSocket = () => {
		// 注意：这里硬编码了 socket 地址，实际项目中建议从配置或 props 获取
		socket.value = new WebSocket('ws://192.168.239.1:8000/ssh_web/');

		socket.value.onopen = () => {
			// 发送认证包
			socket.value.send(JSON.stringify({
				'ip': currentConnection.ip,
				'username': currentConnection.user,
				'password': currentConnection.password
			}));
			// 重新调整一次大小
			if (fitAddon.value) fitAddon.value.fit();
		};

		socket.value.onmessage = (event) => {
			let msg = event.data;
			// 尝试解析后端可能发来的 JSON 提示
			try {
				const jsonObj = JSON.parse(msg);
				if (jsonObj.message) {
					// 如果是纯文本消息提示，可以选择打印到终端或弹窗
					// term.value.write(jsonObj.message + '\r\n');
					return;
				}
			} catch (e) {
				// 忽略解析错误，视为普通流数据
			}
			// 写入终端
			if (term.value) term.value.write(msg);
		};

		socket.value.onclose = () => {
			if (term.value) term.value.write('\r\n\x1b[31m连接已断开\x1b[0m');
			// 注意：这里不要自动清空 currentConnection，保留界面让用户看到断开信息
		};

		socket.value.onerror = () => {
			if (term.value) term.value.write('\r\n\x1b[31m连接发生错误\x1b[0m');
		};
	};

	// 窗口大小调整处理
	const handleResize = () => {
		if (fitAddon.value) {
			// 稍微延迟一下确保 DOM 布局更新完毕
			setTimeout(() => {
				fitAddon.value.fit();
			}, 100);
		}
	};
</script>

<style scoped>
	/* 布局容器：Flex 左右结构 */
	.ssh-container {
		display: flex;
		/* 关键点1：强制占满剩余空间，不许溢出 */
		width: 100%;

		/* 关键点2：根据你的实际情况调整高度 
     如果你知道顶部导航栏高度是 60px，就写 calc(100vh - 60px)
     如果不确定，可以尝试改成 100%，但这依赖父容器高度 */
		height: 100%;

		/* 关键点3：禁止容器本身产生滚动条 */
		overflow: hidden;

		background-color: #f0f2f5;
		box-sizing: border-box;
		/* 防止 padding 撑大宽高 */
	}

	/* 左侧面板样式 */
	.left-panel {
		width: 320px;
		flex-shrink: 0;
		border-right: 1px solid #dcdfe6;
		background: white;
		display: flex;
		flex-direction: column;
		height: 100%;
		/* 确保填满父容器 */
	}
	
	/* 让 card 的 body 部分自动填充剩余高度 */
	:deep(.el-card__body) {
	  height: calc(100% - 55px); /* 减去 header 高度 */
	  display: flex;
	  flex-direction: column;
	  padding: 10px;
	  box-sizing: border-box;
	}

	.card-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		font-weight: bold;
	}

	/* 右侧面板样式 */
	.right-panel {
		flex: 1;
		display: flex;
		flex-direction: column;
		background-color: #1e1e1e;
		/* 与终端背景一致 */
		min-width: 0;
		/* 防止 flex 子项溢出 */
	}

	/* 终端顶部工具栏 */
	.term-header {
		height: 40px;
		background-color: #2c2c2c;
		/* 深灰色顶部 */
		border-bottom: 1px solid #444;
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 15px;
		color: #fff;
	}

	.connection-info .label {
		color: #aaa;
		font-size: 12px;
		margin-right: 8px;
	}

	.connection-info .value {
		color: #fff;
		font-weight: bold;
		font-family: monospace;
	}

	/* 终端主体区域 */
	.term-body {
		flex: 1;
		position: relative;
		/* 用于定位 xterm */
		overflow: hidden;
		padding: 5px;
		/* 留一点边距美观 */
	}

	.xterm-container {
		width: 100%;
		height: 100%;
	}

	/* 占位符样式 */
	.placeholder-text {
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		background: white;
		border-radius: 8px;
		padding: 20px;
	}

	/* 状态点样式 */
	.status-dot {
		width: 10px;
		height: 10px;
		border-radius: 50%;
		margin: 0 auto;
	}

	.status-normal {
		background-color: #67C23A;
		box-shadow: 0 0 4px #67C23A;
	}

	.status-fault {
		background-color: #E6A23C;
	}

	.status-error {
		background-color: #F56C6C;
	}

	.status-unknown {
		background-color: #909399;
	}
</style>