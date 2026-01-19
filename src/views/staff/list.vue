<template>
	<OADialog title="修改员工状态" v-model="dialogVisible" @submit="onSubmitEditStaff">
		<el-form :model="staffForm" label-width="100px">
			<el-form-item label="状态">
				<el-radio-group v-model="staffForm.status" class="ml-4">
					<el-radio :value="1">激活</el-radio>
					<el-radio :value="3">锁定</el-radio>
				</el-radio-group>
			</el-form-item>
		</el-form>
	</OADialog>

	<el-card style="margin-bottom: 10px;">
		<el-form :inline="true" class="my-form-inline">
			<el-form-item label="按部门">
				<el-select v-model="filterForm.department_id">
					<el-option v-for="department in departments" :label="department.name" :value="department.id"
						:key="department.name" />
				</el-select>
			</el-form-item>
			<el-form-item label="按姓名">
				<el-input v-model="filterForm.realname" />
			</el-form-item>
			<el-form-item label="按入职时间">
				<el-date-picker v-model="filterForm.date_joined" type="daterange" range-separator="到"
					start-placeholder="起始日期" end-placeholder="结束日期" format="YYYY-MM-DD" value-format="YYYY-MM-DD" />
			</el-form-item>
			<el-form-item>
				<el-button type="primary" icon="Search" @click="onSearch"></el-button>
			</el-form-item>
			<el-form-item>
				<el-button type="danger" icon="Download" @click="onDownload">下载</el-button>
			</el-form-item>
			<el-form-item>
				<el-upload :action="BASE_URL+'/staff/upload'" :headers="{Authorization: 'JWT '+authStore.token}"
					:on-success="onUploadSuccess" :on-error="onUploadFail" :show-file-list="false" :auto-upload="true"
					accept=".xlsx, .xls">
					<el-button type="danger" icon="Upload">上传</el-button>
				</el-upload>
			</el-form-item>
		</el-form>
	</el-card>

	<el-card>
		<el-table :data="staffs" ref="tableRef">
			<el-table-column type="selection" width="55"></el-table-column>
			<el-table-column label="序号" width="60">
				<template #default="scope">{{ scope.$index + 1 }}</template>
			</el-table-column>
			<el-table-column prop="realname" label="姓名"></el-table-column>
			<el-table-column prop="email" label="邮箱"></el-table-column>
			<el-table-column label="入职时间">
				<template #default="scope">
					{{ timeFormatter.stringFromDate(scope.row.date_joined) }}
				</template>
			</el-table-column>
			<el-table-column prop="department.name" label="部门"></el-table-column>
			<el-table-column label="状态">
				<template #default="scope">
					<el-tag v-if="scope.row.status == 1" type="success">正常</el-tag>
					<el-tag v-else-if="scope.row.status == 2" type="warning">未激活</el-tag>
					<el-tag v-else type="danger">已锁定</el-tag>
				</template>
			</el-table-column>
			<el-table-column label="操作">
				<template #default="scope">
					<el-button type="primary" icon="Edit" circle @click="onEditStaff(scope.$index)"></el-button>
				</template>
			</el-table-column>
		</el-table>

		<template #footer>
			<div style="display: flex; justify-content: space-between;">
				<el-form-item label="每页：">
					<el-select v-model="page_size" size="small" style="width: 100px;">
						<el-option select label="10条/页" :value="1" />
						<el-option label="20条/页" :value="2" />
					</el-select>
				</el-form-item>
				<el-pagination background layout="prev, pager, next" :total="pagination.total"
					v-model:currentPage="pagination.page" :page-size="page_size" />
			</div>
		</template>
	</el-card>
</template>

<script setup name="stafflist">
	import {
		ref,
		reactive,
		onMounted,
		watch
	} from "vue"
	import timeFormatter from "@/utils/timeFormatter";
	import staffHttp from "@/api/staffHttp";
	import {
		ElMessage
	} from "element-plus";
	import OADialog from '@/components/OADialog.vue'
	import { useAuthStore } from "@/stores/auth";
	
	const authStore = useAuthStore()

	let staffs = ref([])
	let pagination = reactive({
		page: 1,
		total: 0
	})
	let page_size = ref(1)
	let dialogVisible = ref(false)
	let staffForm = reactive({
		status: 1
	})
	let handleIndex = 0
	let filterForm = reactive({
		department_id: 1,
		realname: '',
		date_joined: ''
	})
	let departments = ref([])
	let tableRef = ref()
	const BASE_URL = import.meta.env.VITE_BASE_URL


	const onSearch = () => {
		fetchStaffList(1, page_size.value)
	}

	const onDownload = async () => {
		let rows = tableRef.value.getSelectionRows()
		if (!rows || rows.length == 0) {
			// console.log('勾选')
			ElMessage.info('请先选中要导出的员工！')
			return;
		}
		try {
			let response = await staffHttp.downloadStaffs(rows.map(row => row.uid))
			// 借助a标签，将response数据，放到a标签的href属性上，然后模拟点击行为
			// 将返回的二进制数据，创建成一个url对象
			let href = URL.createObjectURL(response.data)
			// 创建a标签
			const a = document.createElement("a")
			a.href = href
			// 设置a标签的download属性，在点击的时候，就会执行下载操作
			a.setAttribute('download', '员工信息.xlsx')
			// 将a标签添加到网页结构中
			document.body.appendChild(a)
			// 模拟点击行为，只要点击了，那么浏览器就会启动下载操作（下载href属性指定的数据）
			a.click()

			// 只要执行了下载，a标签就没用了，就可以从网页中移除了
			document.body.removeChild(a)
			// 移除URL数据
			URL.revokeObjectURL(href)
		} catch (detail) {
			ElMessage.error(detail)
		}
	}

	const onUploadSuccess = () => {
		ElMessage.success('员工上传成功')
		fetchStaffList(1, page_size.value)
	}
	
	const onUploadFail = (error) => {
		const detail = JSON.parse(error.message).detail
		ElMessage.error(detail)
	}

	async function fetchStaffList(page, page_size) {
		try {
			let data = await staffHttp.getStaffList(page, page_size, filterForm)
			pagination.total = data.count
			pagination.page = page
			staffs.value = data.results
		} catch (detail) {
			ElMessage.error(detail)
		}
	}

	onMounted(async () => {
		fetchStaffList(1, page_size.value)

		try {
			let data = await staffHttp.getDepartment()
			departments.value = data.results
		} catch (detail) {
			ElMessage.error(detail)
		}
	})

	watch(() => pagination.page, async function(value) {
		fetchStaffList(value, page_size.value)
	})

	watch(page_size, function(value) {
		if (pagination.page == 1) {
			fetchStaffList(1, value)
		} else {
			pagination.page = 1
		}
	})

	const onEditStaff = (index) => {
		handleIndex = index
		dialogVisible.value = true
		let staff = staffs.value[index]
		staffForm.status = staff.status
	}

	const onSubmitEditStaff = async () => {
		let staff = staffs.value[handleIndex]
		try {
			let newstaff = await staffHttp.updateStaffStatus(staff.uid, staffForm.status)
			ElMessage.success('员工状态修改成功')
			dialogVisible.value = false
			staffs.value.splice(handleIndex, 1, newstaff)
		} catch (detail) {
			ElMessage.error(detail)
		}
	}
</script>

<style>
	.my-form-inline .el-input {
		--el-input-width: 140px;
	}

	.my-form-inline .el-select {
		--el-select-width: 140px;
	}

	.el-form--inline .el-form-item {
		margin-right: 20px;
	}
</style>