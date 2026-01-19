<template>
	<div class="login-container">
		<div class="background-shape shape-1"></div>
		<div class="background-shape shape-2"></div>

		<div class="login-box">
			<div class="login-header">
				<h1 class="brand-title">WHYOPS</h1>
				<p class="brand-subtitle">CMDB & 自动化运维平台</p>
			</div>

			<div class="login-form">
				<div class="input-group">
					<i class="iconfont icon-fa-envelope input-icon"></i>
					<input type="text" v-model="form.email" placeholder="请输入工作邮箱" @keyup.enter="obSubmit" />
					<span class="focus-border"></span>
				</div>

				<div class="input-group">
					<i class="iconfont icon-fa-lock input-icon"></i>
					<input type="password" v-model="form.password" placeholder="请输入密码" @keyup.enter="obSubmit" />
					<span class="focus-border"></span>
				</div>

				<button class="login-btn" @click="obSubmit">
					<span>立即登录</span>
				</button>
			</div>

			<div class="login-footer">
				<p>© 2026 WHYOPS Operation System</p>
			</div>
		</div>
	</div>
</template>

<script setup name='login'>
	import {
		reactive
	} from 'vue';
	import authHttp from '@/api/authHttp'
	import {
		useAuthStore
	} from '@/stores/auth';
	import {
		useRouter
	} from 'vue-router';
	import {
		ElMessage
	} from 'element-plus';

	const authStore = useAuthStore();
	const router = useRouter();

	const form = reactive({
		email: '',
		password: ''
	});

	const obSubmit = async () => {
		if (!form.email) {
			return ElMessage.warning('请输入邮箱');
		}
		if (!form.password) {
			return ElMessage.warning('请输入密码');
		}

		try {
			let data = await authHttp.login(form.email, form.password)
			let token = data.token;
			let user = data.user;

			authStore.setUserToken(user, token);
			ElMessage.success('登录成功');
			router.push({
				name: 'home'
			});
		} catch (detail) {
			const msg = typeof detail === 'object' && detail.message ? detail.message : detail;
			ElMessage.error(msg || '登录失败');
		}
	}
</script>

<style scoped>
	/* 定义 CSS 变量，方便统一管理颜色 */
	.login-container {
		--bg-color: #0f172a;
		--glass-bg: rgba(255, 255, 255, 0.05);
		--glass-border: rgba(255, 255, 255, 0.1);
		--primary-color: #3b82f6;
		--accent-color: #8b5cf6;
		--text-color: #e2e8f0;
		--placeholder-color: #64748b;

		position: relative;
		width: 100%;
		height: 100vh;
		background-color: var(--bg-color);
		display: flex;
		justify-content: center;
		align-items: center;
		overflow: hidden;
		font-family: 'PingFang SC', 'Helvetica Neue', Helvetica, 'microsoft yahei', arial, sans-serif;
	}

	/* --- 动态背景球 --- */
	.background-shape {
		position: absolute;
		border-radius: 50%;
		filter: blur(80px);
		z-index: 0;
		animation: float 10s infinite ease-in-out;
	}

	.shape-1 {
		width: 400px;
		height: 400px;
		background: linear-gradient(135deg, var(--primary-color), #2dd4bf);
		top: -100px;
		left: -100px;
	}

	.shape-2 {
		width: 300px;
		height: 300px;
		background: linear-gradient(135deg, var(--accent-color), #ec4899);
		bottom: -50px;
		right: -50px;
		animation-delay: -5s;
	}

	@keyframes float {

		0%,
		100% {
			transform: translate(0, 0);
		}

		50% {
			transform: translate(20px, 40px);
		}
	}

	/* --- 登录卡片 (毛玻璃) --- */
	.login-box {
		position: relative;
		width: 400px;
		padding: 40px;
		background: var(--glass-bg);
		backdrop-filter: blur(20px);
		/* 核心毛玻璃属性 */
		-webkit-backdrop-filter: blur(20px);
		border: 1px solid var(--glass-border);
		border-radius: 16px;
		box-shadow: 0 15px 35px rgba(0, 0, 0, 0.2);
		z-index: 1;
		color: var(--text-color);
	}

	.login-header {
		text-align: center;
		margin-bottom: 40px;
	}

	.brand-title {
		font-size: 32px;
		font-weight: 800;
		margin: 0;
		letter-spacing: 2px;
		background: linear-gradient(to right, #60a5fa, #c084fc);
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
		text-transform: uppercase;
	}

	.brand-subtitle {
		font-size: 14px;
		color: #94a3b8;
		margin-top: 8px;
		letter-spacing: 1px;
	}

	/* --- 输入框组 --- */
	.input-group {
		position: relative;
		margin-bottom: 30px;
	}

	.input-icon {
		position: absolute;
		left: 0;
		top: 10px;
		font-size: 18px;
		color: var(--placeholder-color);
		transition: color 0.3s;
	}

	.input-group input {
		width: 100%;
		padding: 10px 10px 10px 30px;
		background: transparent;
		border: none;
		border-bottom: 1px solid #475569;
		color: #fff;
		font-size: 16px;
		outline: none;
		transition: all 0.3s;
		box-sizing: border-box;
	}

	.input-group input::placeholder {
		color: var(--placeholder-color);
	}

	.input-group input:focus {
		border-bottom-color: transparent;
	}

	/* 兄弟选择器：当input聚焦时，改变icon颜色 */
	.input-group input:focus~.input-icon {
		color: var(--primary-color);
	}

	/* 兄弟选择器：当input聚焦时，展开底线 */
	.input-group input:focus+.focus-border {
		width: 100%;
	}

	/* 动态底线动画 */
	.focus-border {
		position: absolute;
		bottom: 0;
		left: 0;
		width: 0;
		height: 2px;
		background: linear-gradient(to right, var(--primary-color), var(--accent-color));
		transition: width 0.4s ease;
	}

	/* --- 登录按钮 --- */
	.login-btn {
		width: 100%;
		height: 45px;
		background: linear-gradient(90deg, var(--primary-color), var(--accent-color));
		border: none;
		border-radius: 25px;
		color: white;
		font-size: 16px;
		font-weight: 600;
		cursor: pointer;
		position: relative;
		overflow: hidden;
		transition: transform 0.2s, box-shadow 0.2s;
		letter-spacing: 1px;
	}

	.login-btn:hover {
		transform: translateY(-2px);
		box-shadow: 0 5px 15px rgba(59, 130, 246, 0.4);
	}

	.login-btn:active {
		transform: translateY(0);
	}

	.login-footer {
		text-align: center;
		margin-top: 30px;
	}

	.login-footer p {
		font-size: 12px;
		color: rgba(255, 255, 255, 0.3);
	}
</style>