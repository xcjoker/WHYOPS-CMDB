<template>
	<el-card>
		<template #header>
			<div style="text-align: center;">
				<h2>{{ inform.title }}</h2>
			<el-space>
				<span>作者: {{ inform.author.realname }}</span>
				<span>发布时间: {{ timeFormatter.stringFromDate(inform.create_time) }}</span>
			</el-space>
			</div>
		</template>
		<template #default>
			<div v-html="inform.content" class="content"></div>
		</template>
		<template #footer>
			<div>阅读量: {{ inform.read_count }}</div>
		</template>
	</el-card>
</template>

<script setup name='detailinform'>
	import {
		ref,
		reactive,
		onMounted
	} from "vue"
	import OAPagination from "@/components/OAPagination.vue";
	import timeFormatter from "@/utils/timeFormatter"
	import {
		useAuthStore
	} from "@/stores/auth";
	import informHttp from "@/api/informHttp";
	import {
		ElMessage,
		ElMessageBox
	} from "element-plus";
	import OADialog from "@/components/OADialog.vue"
	import {
		useRoute
	} from "vue-router";

	const route = useRoute()
	let inform = reactive({
		title: "",
		content: "",
		create_time: "",
		author: {
			realname: "",
		}
	})

	onMounted(async () => {
		try {
			const pk = route.params.pk
			let data = await informHttp.getInformDetail(pk)
			Object.assign(inform, data) //把data的值赋值给inform
			await informHttp.readInform(pk)
		} catch (detail) {
			ElMessage.error(detail)
		}
		//发送请求，用于阅读通知
		
	})
</script>

<style scoped>
	.content :deep(img){
		max-width: 100%;
	}
</style>