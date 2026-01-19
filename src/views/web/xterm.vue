<template>
	<div id="xterm" class="xterm" />
</template>

<script setup>
	import {
		ref,
		onMounted,
		onBeforeUnmount
	} from 'vue';
	import 'xterm/css/xterm.css';
	import {
		Terminal
	} from 'xterm';
	import {
		FitAddon
	} from 'xterm-addon-fit';
	// 移除 AttachAddon，我们要手动控制接收逻辑
	// import { AttachAddon } from 'xterm-addon-attach'; 
	import {
		eventBus
	} from "@/event/eventBus"

	// 定义响应式变量
	const socket = ref(null);
	const term = ref(null);
	const fitAddon = ref(null); // 保存 fitAddon 实例以便 resize
	let ip = eventBus.ip
	let password = eventBus.password
	let username = eventBus.user

	// 初始化终端
	const initTerm = () => {
		const newTerm = new Terminal({
			fontFamily: '"Cascadia Code", monospace',
			fontSize: 20,
			cursorBlink: true,
			rendererType: "canvas",
			rows: 40,
			cols: 100,
			convertEol: true,
			disableStdin: false,
			windowsMode: true,
			cursorStyle: "underline",
			scrollback: 1000,
			theme: {
				foreground: "#ECECEC",
				background: "#24486d",
				cursor: "help",
				lineHeight: 30,
			},
		});

		// const attachAddon = new AttachAddon(socket.value, { bidirectional: false }); // 删除
		const fit = new FitAddon();
		fitAddon.value = fit;

		// newTerm.loadAddon(attachAddon); // 删除
		newTerm.loadAddon(fit);
		newTerm.open(document.getElementById('xterm'));
		fit.fit();
		newTerm.focus();
		// newTerm.write('等待连接...') // 这句话可以不要，看后端返回

		term.value = newTerm;

		// 监听窗口大小变化
		window.addEventListener('resize', () => {
			if (fitAddon.value) fitAddon.value.fit();
		});

		// --- 核心修改：透传模式 ---
		// 不再进行任何本地缓冲，不再 slice 删除键，不再等待回车
		term.value.onData((val) => {
			// 直接发送每一个按键动作给后端
			// 如果你按了 'ls'，这里会触发两次：一次 'l'，一次 's'
			// 如果你按了删除，这里会触发 '\x7f'，直接发给后端，后端 Shell 会处理删除逻辑并把处理后的结果发回来
			if (socket.value && socket.value.readyState === 1) {
				socket.value.send(JSON.stringify({
					'command': val
				}));
			}
		});
	};

	// 初始化 WebSocket
	const initSocket = () => {
		socket.value = new WebSocket('ws://192.168.239.1:8000/ssh_web/');
		socketOnOpen();
		socketOnMessage(); // 新增消息监听
		socketOnClose();
		socketOnError();
	};

	// 处理 WebSocket 打开事件
	const socketOnOpen = () => {
		socket.value.onopen = () => {
			socket.value.send(JSON.stringify({
				'ip': ip,
				'username': username,
				'password': password,
				// 'command': '' // 这一行其实不需要了，连接包只发认证信息即可
			}))
			initTerm();
		};
	};

	// --- 新增：手动处理服务端发回来的数据 ---
	const socketOnMessage = () => {
		socket.value.onmessage = (event) => {
			// 后端逻辑有点乱：连接成功发的是 JSON，SSH流发的是纯文本
			// 我们尝试解析一下，如果是 JSON 且包含 message 就当提示打印，否则直接写入终端
			try {
				// 尝试解析 JSON (针对后端发的 {'message': 'Connect Success'})
				const data = JSON.parse(event.data);
				if (data && data.message) {
					term.value.write(data.message);
					return; // 如果是系统提示，打印完就结束
				}
			} catch (e) {
				// 解析失败说明不是 JSON，而是普通的 SSH 数据流 (shell output)
				// 直接写入终端，xterm 会自动解析 \r \n \b 和 颜色代码
			}

			// 无论如何，如果是普通数据，直接写进终端
			// 注意：这里需要配合上面的 try-catch 逻辑，
			// 简单粗暴的做法是：如果 try 成功了且是 message，就不走下面；否则走下面。
			// 修正后的逻辑如下：

			let msg = event.data;
			try {
				const jsonObj = JSON.parse(msg);
				if (jsonObj.message) {
					msg = jsonObj.message; // 提取提示信息
				}
			} catch (e) {
				// 不是 JSON，原样输出
			}
			term.value.write(msg);
		};
	};

	const socketOnClose = () => {
		socket.value.onclose = () => {
			if (term.value) term.value.write('\r\n连接已断开');
		};
	};

	const socketOnError = () => {
		socket.value.onerror = () => {
			if (term.value) term.value.write('\r\n连接错误');
		};
	};

	onMounted(() => {
		initSocket();
	});

	onBeforeUnmount(() => {
		if (socket.value) {
			socket.value.close();
		}
		if (term.value) {
			term.value.dispose();
		}
	});
</script>

<style scoped>
	.xterm {
		height: 100vh;
		width: 100%;
		background-color: #24486d;
		/* 防止加载慢时白屏 */
	}
</style>