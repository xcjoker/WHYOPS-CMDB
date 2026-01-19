<template>
	<el-container class="container">
		<el-aside class='aside' :width="asideWidth">
			<router-link to="/" class="brand">
				<div class="logo-wrapper">
					<el-icon class="logo-icon" size="24" color="#409EFF" v-if="!isCollapse">
						<ElementPlus />
					</el-icon>
					<span v-show="!isCollapse" class="brand-text">WHY<span class="brand-accent">OPS</span></span>
					<span v-show="isCollapse" class="brand-text-mini">W</span>
				</div>
			</router-link>

			<el-menu active-text-color="#ffffff" background-color="#001529" class="el-menu-vertical-demo"
				default-active="1" text-color="#a6adb4" :collapse="isCollapse" :collapse-transition="false"
				unique-opened>
				<el-menu-item index="1" @click="goToHome">
					<el-icon>
						<HomeFilled />
					</el-icon>
					<span>首页</span>
				</el-menu-item>

				<el-sub-menu index="2">
					<template #title>
						<el-icon>
							<Avatar />
						</el-icon>
						<span>员工管理</span>
					</template>
					<el-menu-item index="2-1" @click="$router.push({ name: 'staff_add' })">
						<el-icon>
							<CirclePlusFilled />
						</el-icon>
						<span>新增员工</span>
					</el-menu-item>
					<el-menu-item index="2-2" @click="$router.push({ name: 'staff_list' })">
						<el-icon>
							<List />
						</el-icon>
						<span>员工列表</span>
					</el-menu-item>
				</el-sub-menu>

				<el-sub-menu index="3">
					<template #title>
						<el-icon>
							<BellFilled />
						</el-icon>
						<span>通知管理</span>
					</template>
					<el-menu-item index="3-1" @click="$router.push({ name: 'inform_publish' })">
						<el-icon>
							<CirclePlusFilled />
						</el-icon>
						<span>发布通知</span>
					</el-menu-item>
					<el-menu-item index="3-2" @click="$router.push({ name: 'inform_list' })">
						<el-icon>
							<List />
						</el-icon>
						<span>通知列表</span>
					</el-menu-item>
				</el-sub-menu>

				<el-sub-menu index="4">
					<template #title>
						<el-icon>
							<Checked />
						</el-icon>
						<span>主机管理</span>
					</template>
					<el-menu-item index="4-1" @click="goToIdcRegion">
						<el-icon>
							<UserFilled />
						</el-icon>
						<span>机房管理</span>
					</el-menu-item>
					<el-menu-item index="4-2" @click="router.push({name: 'server'})">
						<el-icon>
							<User />
						</el-icon>
						<span>物理服务器管理</span>
					</el-menu-item>
				</el-sub-menu>





				<el-menu-item index="5" @click="router.push({name: 'web'})">
					<el-icon>
						<Monitor />
					</el-icon>
					<span>终端连接</span>
				</el-menu-item>

				<el-menu-item index="6" @click="goToCluster">
					<el-icon>
						<Odometer />
					</el-icon>
					<span>集群概览</span>
				</el-menu-item>

				<el-sub-menu index="7">
					<template #title>
						<el-icon>
							<Grid />
						</el-icon>
						<span>工作负载</span>
					</template>
					<el-menu-item index="7-1" @click="goToPodInfo">
						<el-icon>
							<Box />
						</el-icon>
						<span>Pod</span>
					</el-menu-item>
					<el-menu-item index="7-2" @click="goToDeploymentInfo">
						<el-icon>
							<CopyDocument />
						</el-icon>
						<span>Deployment</span>
					</el-menu-item>
					<el-menu-item index="7-3" @click="goToStatefulSetInfo">
						<el-icon>
							<Files />
						</el-icon>
						<span>StatefulSet</span>
					</el-menu-item>
					<el-menu-item index="7-4" @click="goToDaemonSetInfo">
						<el-icon>
							<Platform />
						</el-icon>
						<span>DaemonSet</span>
					</el-menu-item>
					<el-menu-item index="7-5" @click="goToJobInfo">
						<el-icon>
							<Aim />
						</el-icon>
						<span>Job</span>
					</el-menu-item>
					<el-menu-item index="7-6" @click="goToCronJobInfo">
						<el-icon>
							<AlarmClock />
						</el-icon>
						<span>CronJob</span>
					</el-menu-item>
				</el-sub-menu>
				
				<el-sub-menu index="8">
					<template #title>
						<el-icon>
							<Files />
						</el-icon>
						<span>存储</span>
					</template>
					<el-menu-item index="8-1" @click="goToPVInfo">
						<el-icon>
							<Coin />
						</el-icon>
						<span>PV</span>
					</el-menu-item>
					<el-menu-item index="8-2" @click="goToPVCInfo">
						<el-icon>
							<Ticket />
						</el-icon>
						<span>PVC</span>
					</el-menu-item>
					<el-menu-item index="8-3" @click="goToStorageClassCInfo">
						<el-icon>
							<Suitcase />
						</el-icon>
						<span>StorageClass</span>
					</el-menu-item>
				</el-sub-menu>
				
				<el-sub-menu index="9">
					<template #title>
						<el-icon>
							<Share />
						</el-icon>
						<span>网络</span>
					</template>
					<el-menu-item index="9-1" @click="goToServiceInfo">
						<el-icon>
							<Connection />
						</el-icon>
						<span>Service</span>
					</el-menu-item>
					<el-menu-item index="9-2" @click="goToIngressInfo">
						<el-icon>
							<Link />
						</el-icon>
						<span>Ingress</span>
					</el-menu-item>
				</el-sub-menu>
			</el-menu>
		</el-aside>

		<el-container>
			<el-header class="header">
				<div class="left-header">
					<el-icon class="trigger-icon" @click="onCollapseAside" :size="24">
						<component :is="isCollapse ? Expand : Fold" />
					</el-icon>
				</div>

				<el-dropdown trigger="click">
					<span class="el-dropdown-link user-info">
						<el-avatar :size="32" icon="UserFilled" style="background-color: #409EFF;" />
						<span class="username">
							<span class="dept-tag">{{ authStore.user?.department?.name || '部门' }}</span>
							{{ authStore.user?.realname || '用户' }}
						</span>
						<el-icon class="el-icon--right">
							<CaretBottom />
						</el-icon>
					</span>
					<template #dropdown>
						<el-dropdown-menu class="user-dropdown">
							<el-dropdown-item @click="onControlResetPwdDialog">修改密码</el-dropdown-item>
							<el-dropdown-item divided @click="onExit">退出登录</el-dropdown-item>
						</el-dropdown-menu>
					</template>
				</el-dropdown>
			</el-header>

			<el-main class="main">
				<slot></slot>
				<router-view></router-view>
			</el-main>
		</el-container>
	</el-container>

	<el-dialog v-model="dialogVisible" title="修改密码" width="500">
		<el-form :model="resetPwdForm" :rules="rules" ref="formTag">
			<el-form-item label="旧密码" :label-width="formLabelWidth" prop="oldpwd">
				<el-input v-model="resetPwdForm.oldpwd" autocomplete="off" type="password" />
			</el-form-item>
			<el-form-item label="新密码" :label-width="formLabelWidth" prop="pwd1">
				<el-input v-model="resetPwdForm.pwd1" autocomplete="off" type="password" />
			</el-form-item>
			<el-form-item label="确认密码" :label-width="formLabelWidth" prop="pwd2">
				<el-input v-model="resetPwdForm.pwd2" autocomplete="off" type="password" />
			</el-form-item>
		</el-form>
		<template #footer>
			<div class="dialog-footer">
				<el-button @click="dialogVisible = false">取消</el-button>
				<el-button type="primary" @click="onsubmit">确认</el-button>
			</div>
		</template>
	</el-dialog>
</template>

<script setup name='frame'>
	import {
		ref,
		computed,
		reactive
	} from 'vue';
	import {
		useRouter
	} from 'vue-router';
	import {
		useAuthStore
	} from "@/stores/auth"
	import authHttp from '@/api/authHttp';
	import {
		ElMessage
	} from 'element-plus';

	// *** 关键修复：引入所有用到的图标 ***
	import {
		Expand,
		Fold,
		HomeFilled,
		Checked,
		UserFilled,
		User,
		BellFilled,
		CirclePlusFilled,
		List,
		Avatar,
		Monitor,
		Odometer, // 新增
		ElementPlus, // 新增
		CaretBottom // 新增
	} from '@element-plus/icons-vue'

	const authStore = useAuthStore()
	const router = useRouter()

	// 增加可选链判断，防止 authStore.user 为空时报错
	console.log(authStore.user)

	let isCollapse = ref(false)
	let asideWidth = computed(() => {
		if (isCollapse.value) {
			return "64px"
		} else {
			return "220px" // 调整了展开宽度，更紧凑
		}
	})

	const onCollapseAside = () => {
		isCollapse.value = !isCollapse.value
	}

	let dialogVisible = ref(false)
	let resetPwdForm = reactive({
		oldpwd: '',
		pwd1: '',
		pwd2: ''
	})
	let formLabelWidth = '100px'
	let rules = reactive({
		oldpwd: [{
				required: true,
				message: '请输入旧密码',
				trigger: 'blur'
			},
			{
				min: 6,
				max: 20,
				message: '密码长度需要在6-20之间',
				trigger: 'blur'
			},
		],
		pwd1: [{
				required: true,
				message: '请输入新密码',
				trigger: 'blur'
			},
			{
				min: 6,
				max: 20,
				message: '密码长度需要在6-20之间',
				trigger: 'blur'
			},
		],
		pwd2: [{
				required: true,
				message: '请输入确认密码',
				trigger: 'blur'
			},
			{
				min: 6,
				max: 20,
				message: '密码长度需要在6-20之间',
				trigger: 'blur'
			},
		]
	})
	let formTag = ref()

	const goToIdcRegion = () => {
		router.push({
			name: 'region'
		})
	}

	const goToHome = () => {
		router.push({
			name: 'home'
		})
	}

	const goToCluster = () => {
		router.push({
			name: 'info'
		})
	}

	const onExit = () => {
		authStore.clearUserToken()
		router.push({
			name: 'login'
		})
	}

	const goToPodInfo = () => {
		router.push({
			name: 'pod'
		})
	}

	const goToDeploymentInfo = () => {
		router.push({
			name: 'deployment'
		})
	}

	const goToStatefulSetInfo = () => {
		router.push({
			name: 'statefulset'
		})
	}

	const goToDaemonSetInfo = () => {
		router.push({
			name: 'daemonset'
		})
	}

	const goToJobInfo = () => {
		router.push({
			name: 'job'
		})
	}

	const goToCronJobInfo = () => {
		router.push({
			name: 'cronjob'
		})
	}
	
	const goToPVInfo = () => {
		router.push({
			name: 'pv'
		})
	}
	
	const goToPVCInfo = () => {
		router.push({
			name: 'pvc'
		})
	}
	
	const goToStorageClassCInfo = () => {
		router.push({
			name: 'storageclass'
		})
	}
	
	const goToServiceInfo = () => {
		router.push({
			name: 'service'
		})
	}
	
	const goToIngressInfo = () => {
		router.push({
			name: 'ingress'
		})
	}

	const onsubmit = () => {
		formTag.value.validate(async (valid, fields) => {
			if (valid) {
				try {
					await authHttp.resetPwd(resetPwdForm.oldpwd, resetPwdForm.pwd1, resetPwdForm.pwd2)
					ElMessage.success('密码修改成功')
					dialogVisible.value = false
				} catch (detail) {
					ElMessage.error(detail)
				}
			} else {
				ElMessage.info('请按要求填写字段')
			}
		})
	}

	const onControlResetPwdDialog = () => {
		resetPwdForm.oldpwd = ''
		resetPwdForm.pwd1 = ''
		resetPwdForm.pwd2 = ''
		dialogVisible.value = true
	}
</script>

<style scoped>
	/* 全局容器 */
	.container {
		height: 100vh;
		background-color: #f0f2f5;
	}

	/* 侧边栏 */
	.aside {
		background-color: #001529;
		transition: width 0.3s;
		box-shadow: 2px 0 6px rgba(0, 21, 41, 0.35);
		z-index: 10;
		overflow-x: hidden;
		display: flex;
		flex-direction: column;
	}

	/* Logo 区域 */
	.aside .brand {
		height: 64px;
		background-color: #002140;
		display: flex;
		justify-content: center;
		align-items: center;
		text-decoration: none;
		overflow: hidden;
	}

	.logo-wrapper {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.brand-text {
		color: #fff;
		font-size: 20px;
		font-weight: 700;
		white-space: nowrap;
		/* 防止文字换行 */
	}

	.brand-accent {
		color: #409EFF;
		font-weight: 400;
	}

	.brand-text-mini {
		color: #409EFF;
		font-size: 24px;
		font-weight: bold;
	}

	/* 菜单 */
	.el-menu {
		border-right: none;
	}

	/* 头部 */
	.header {
		height: 64px;
		background-color: #fff;
		border-bottom: 1px solid #e6e6e6;
		box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0 24px;
	}

	.trigger-icon {
		cursor: pointer;
		color: #5a5e66;
		transition: color 0.3s;
	}

	.trigger-icon:hover {
		color: #409EFF;
	}

	/* 用户信息 */
	.user-info {
		display: flex;
		align-items: center;
		cursor: pointer;
		padding: 5px 8px;
		border-radius: 4px;
	}

	.user-info:hover {
		background-color: rgba(0, 0, 0, 0.025);
	}

	.username {
		margin-left: 10px;
		font-size: 14px;
		color: #333;
		display: flex;
		flex-direction: column;
		line-height: 1.2;
	}

	.dept-tag {
		font-size: 12px;
		color: #999;
	}

	.el-icon--right {
		color: #999;
		margin-left: 5px;
	}

	/* 主内容区 */
	.main {
		padding: 20px;
		overflow-y: auto;
		/* 移除白色背景，让卡片自己决定背景，或者保留白色背景但去掉 important */
		/* background-color: #FFFFFF;  */
	}
</style>