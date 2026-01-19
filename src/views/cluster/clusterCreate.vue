<template>
	<frame>
		<div class="create-cluster-container">
			<el-card shadow="never" class="box-card">
				<template #header>
					<div class="card-header">
						<span class="title">导入 Kubernetes 集群</span>
						<el-button style="float: right; padding: 3px 0" text @click="goBack">返回列表</el-button>
					</div>
				</template>

				<el-alert title="将 Kubernetes 集群导入到平台之后，并不影响 Kubernetes 集群的独立性。也就是说，即使在平台不可用的情况下，Kubernetes 集群仍然可以正常工作。"
					type="info" show-icon :closable="false" class="mb-20" />

				<el-form ref="formRef" :model="form" :rules="rules" label-width="100px" label-position="right"
					status-icon>
					<el-form-item label="集群名称：" prop="name">
						<el-input v-model="form.name" placeholder="请输入集群名称" clearable />
					</el-form-item>

					<el-form-item label="集群描述：" prop="description">
						<el-input v-model="form.description" placeholder="请输入集群描述" type="textarea" :rows="2" />
					</el-form-item>

					<el-form-item label="kubeconfig：" prop="kubeconfig">
						<div class="editor-container">
							<div class="editor-toolbar">
								<span>编辑主题 (深色) material-palenight</span>
							</div>
							<el-input v-model="form.kubeconfig" type="textarea" :rows="18"
								placeholder='请将您的 "/etc/kubernetes/admin.conf" 文件粘贴到此处...' class="code-editor"
								@input="handleKubeconfigInput" />
						</div>
					</el-form-item>

					<el-form-item label="context：" prop="context">
						<el-select v-model="form.context" placeholder="请先在代码区粘贴文件内容" style="width: 100%"
							@change="handleContextChange">
							<el-option v-for="item in contextOptions" :key="item.value" :label="item.label"
								:value="item.value" />
						</el-select>
					</el-form-item>

					<el-form-item label="apiServer：" prop="api_server">
						<el-input v-model="form.api_server" placeholder="请输入 apiServerUrl" />
					</el-form-item>

					<el-form-item>
						<div class="form-footer">
							<el-button @click="goBack">取消</el-button>

							<el-tooltip content="即将在27684端口以DaemonSet部署node-exporter" placement="top">
								<span>
									<el-button type="primary" @click="submitForm(formRef)" :loading="submitting">
										导入集群
									</el-button>
								</span>
							</el-tooltip>
						</div>
					</el-form-item>

				</el-form>
			</el-card>
		</div>
	</frame>
</template>

<script setup>
	import {
		reactive,
		ref
	} from 'vue'
	import {
		useRouter
	} from 'vue-router'
	import {
		ElMessage
	} from 'element-plus'
	import yaml from 'js-yaml' // 引入 yaml 解析库
	import clusterHttp from "@/api/clusterHttp"
	import frame from "@/views/main/frame.vue"
	import {
		ElTooltip
	} from 'element-plus'

	const router = useRouter()
	const formRef = ref(null)
	const submitting = ref(false)

	const form = reactive({
		name: '',
		description: '',
		kubeconfig: '',
		context: '',
		api_server: '' // 这里的 key 要和后端 serializer 接收的字段名一致
	})

	const contextOptions = ref([])
	// 用于暂存解析后的完整对象，以便切换 context 时查找对应的 server
	const parsedKubeconfigObj = ref(null)

	const rules = reactive({
		name: [{
				required: true,
				message: '请输入集群名称',
				trigger: 'blur'
			},
			{
				min: 3,
				max: 50,
				message: '长度在 3 到 50 个字符',
				trigger: 'blur'
			}
		],
		kubeconfig: [{
			required: true,
			message: '请填入 Kubeconfig 内容',
			trigger: 'blur'
		}],
		context: [{
			required: true,
			message: '请选择 Context',
			trigger: 'change'
		}],
		api_server: [{
			required: true,
			message: '请输入 ApiServer 地址',
			trigger: 'blur'
		}]
	})

	// 核心逻辑：解析 Kubeconfig
	const handleKubeconfigInput = (val) => {
		if (!val) {
			contextOptions.value = []
			parsedKubeconfigObj.value = null
			return
		}

		try {
			// 使用 js-yaml 解析字符串
			const result = yaml.load(val)
			parsedKubeconfigObj.value = result

			// 1. 提取所有 Context 选项
			if (result.contexts && Array.isArray(result.contexts)) {
				contextOptions.value = result.contexts.map(ctx => ({
					label: ctx.name,
					value: ctx.name
				}))
			}

			// 2. 自动选中 current-context
			if (result['current-context']) {
				form.context = result['current-context']
				// 触发一次 Context 变更逻辑以填充 apiServer
				handleContextChange(form.context)
			}

		} catch (e) {
			// 解析出错时不强行提示，避免用户在打字过程中一直弹窗
			console.warn('YAML 解析失败，可能是格式未完成', e)
		}
	}

	// 当 Context 改变时，自动查找对应的 Cluster Server
	const handleContextChange = (selectedContextName) => {
		if (!parsedKubeconfigObj.value) return

		const config = parsedKubeconfigObj.value

		// 1. 找到 context 对象
		const contextItem = config.contexts.find(c => c.name === selectedContextName)
		if (!contextItem) return

		// 2. 获取该 context 关联的 cluster 名称
		const clusterName = contextItem.context.cluster

		// 3. 在 clusters 数组中找到对应的 cluster 对象
		const clusterItem = config.clusters.find(c => c.name === clusterName)

		// 4. 提取 server 地址并赋值
		if (clusterItem && clusterItem.cluster && clusterItem.cluster.server) {
			form.api_server = clusterItem.cluster.server
		} else {
			form.api_server = '' // 未找到则清空
		}
	}

	const submitForm = async (formEl) => {
		if (!formEl) return
		await formEl.validate(async (valid) => {
			if (valid) {
				submitting.value = true
				try {
					// 2. 调用 API 发送数据
					// 注意：http.js 的 post 方法里已经处理了 .data，并会在 catch 里返回 detail
					const res = await clusterHttp.createCluster(form)

					ElMessage.success(`集群 "${res.name}" 导入成功，版本: ${res.version}`)

					// 3. 成功后跳转到 Info 页面
					router.push({
						name: 'info'
					})

				} catch (err) {
					// 4. 错误处理
					// http.js 的 reject(detail) 会把后端返回的 "连接集群失败..." 传到这里
					console.error(err)
					ElMessage.error(err || '导入失败，请检查网络或配置')
				} finally {
					submitting.value = false
				}
			}
		})
	}

	const goBack = () => {
		router.go(-1)
	}
</script>

<style scoped>
	.create-cluster-container {
		padding: 20px;
		background-color: #f5f7fa;
		min-height: 100vh;
	}

	.box-card {
		border-radius: 4px;
	}

	.title {
		font-size: 16px;
		font-weight: bold;
		color: #303133;
	}

	.mb-20 {
		margin-bottom: 20px;
	}

	.editor-container {
		border: 1px solid #dcdfe6;
		border-radius: 4px;
		overflow: hidden;
		width: 100%;
		/* 确保宽度撑满 */
	}

	.editor-toolbar {
		background-color: #f5f7fa;
		padding: 6px 12px;
		font-size: 12px;
		color: #909399;
		border-bottom: 1px solid #dcdfe6;
	}

	/* 样式优化：调整行高和字体，让编辑器看起来更宽敞专业 */
	.code-editor :deep(.el-textarea__inner) {
		background-color: #292d3e;
		color: #a6accd;
		font-family: 'Menlo', 'Monaco', 'Consolas', monospace;
		/* 优化字体栈 */
		font-size: 13px;
		border: none;
		border-radius: 0;
		line-height: 1.6;
		/* 增加行高 */
		padding: 12px;
		box-shadow: none;
	}

	.code-editor :deep(.el-textarea__inner:focus) {
		box-shadow: none;
		background-color: #292d3e;
	}

	.form-footer {
		display: flex;
		justify-content: flex-end;
		width: 100%;
	}
</style>