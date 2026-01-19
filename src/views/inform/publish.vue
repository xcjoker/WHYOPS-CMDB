<template>
	<el-card>
		<el-form :model="informForm" :rules="rules" ref="formRef">
			<el-form-item label="标题" :label-width="formLabelWidth" prop="title">
				<el-input v-model="informForm.title" autocomplete="off" />
			</el-form-item>
			<el-form-item label="内容" :label-width="formLabelWidth" prop="content">
				<div style="border: 1px solid #ccc; width: 100%;">
					<Toolbar style="border-bottom: 1px solid #ccc" :editor="editorRef" :defaultConfig="toolbarConfig"
						:mode="mode" />
					<Editor style="height: 500px; overflow-y: hidden;" v-model="informForm.content"
						:defaultConfig="editorConfig" :mode="mode" @onCreated="handleCreated" />
				</div>
			</el-form-item>
			<el-form-item>
				<div style="text-align: right; flex: 1;">
					<el-button type="primary" @click="onSubmit">提交</el-button>
				</div>
			</el-form-item>
		</el-form>
	</el-card>
</template>

<script setup name='publishinform'>
	import {
		ref,
		reactive,
		onMounted,
		onBeforeUnmount,
		shallowRef
	} from "vue"
	import '@wangeditor/editor/dist/css/style.css'
	import {
		Editor,
		Toolbar
	} from '@wangeditor/editor-for-vue'
	import {
		ElMessage
	} from "element-plus";
	import {
		useAuthStore
	} from "@/stores/auth";
	import {
		dataTool
	} from "echarts";
	import informHttp from "@/api/informHttp"
	import { useRouter } from 'vue-router';

	let informForm = reactive({
		title: '',
		content: ''
	})
	const rules = reactive({
		title: [{
			required: true,
			message: '请输入标题',
			trigger: 'blur'
		}],
		content: [{
			required: true,
			message: '请输入内容',
			trigger: 'blur'
		}],
	})
	const authStore = useAuthStore()
	let formRef = ref()
	let formLabelWidth = "100px"

	//wangEditor
	// 编辑器实例，必须用 shallowRef
	const editorRef = shallowRef()

	const toolbarConfig = {}
	const editorConfig = {
		placeholder: '请输入内容...',
		MENU_CONF: {
			uploadImage: {
				server: import.meta.env.VITE_BASE_URL + '/image/upload',
				fieldName: 'image',
				maxFileSize: 5 * 1024 * 1024,  //写了这行如果不满足，则不向后端发送请求了
				maxNumberOfFiles: 10,
				allowedFileTypes: ['image/*'],
				headers: {
					Authorization: "JWT " + authStore.token
				},
				timeout: 6 * 1000, // 6 秒
				customInsert(res, insertFn) { // JS 语法
					// res 即服务端的返回结果
					if(res.errno == 0){
						let data = res.data
						let url = import.meta.env.VITE_BASE_URL + data.url
						let href = import.meta.env.VITE_BASE_URL + data.href
						let alt = data.alt
						// 从 res 中找到 url alt href ，然后插入图片
						insertFn(url, alt, href)
					}else{
						ElMessage.error(res.message)
					}
				},
				// 单个文件上传失败
				onFailed(file, res) {
					console.log(`${file.name} 上传失败`, res)
				},

				// 上传错误，或者触发 timeout 超时
				onError(file, err, res) {
					if(file.size > 5 * 1024 * 1024){
						ElMessage.error('图片文件最大不能超过5M!')
					}
					else{
						ElMessage.error('图片格式不正确!')
					}
				},
			}
		}
	}
	// editorConfig.MENU_CONF['uploadImage']
	let mode = 'default'

	// 组件销毁时，也及时销毁编辑器
	onBeforeUnmount(() => {
		const editor = editorRef.value
		if (editor == null) return
		editor.destroy()
	})

	const handleCreated = (editor) => {
		editorRef.value = editor // 记录 editor 实例，重要！
	}
	
	const router = useRouter();
	const onSubmit = () => {
		formRef.value.validate(async(valid, fields) => {
			if (valid) {
				console.log(informForm)
				try{
					let data = await informHttp.publishInform(informForm)
					console.log(data)
					ElMessage.success('发布成功'); // 消息字符串需要用引号包裹
					window.setTimeout(function() {
						router.push({ name: 'inform_list' }); // 修正双层大括号为单层大括号
					}, 600)

				}
				catch(detail){
					ElMessage.error(detail)
				}
			}
		})
	}
</script>

<style>
</style>