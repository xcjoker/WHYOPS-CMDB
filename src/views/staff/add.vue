<script setup name="staffadd">
	import {
		ref,
		reactive,
		onMounted
	} from 'vue';
	import staffHttp from '@/api/staffHttp';
	import {
		useRouter
	} from 'vue-router';
	import {
		useAuthStore
	} from "@/stores/auth"
	import {
		ElMessage
	} from 'element-plus';


	const router = useRouter();
	const authStore = useAuthStore()
	const departmentList = ref([]); // 存储部门数据
	// const selectedDepartment = ref('')
	const leader_name = ref('')

	// 只有部门的leader可以给本部门新增员工
	let staffForm = reactive({
		email: "",
		password: "",
		realname: "",
		selectedDepartment: ''
	});
	const formRef = ref()
	let rules = reactive({
		email: [{
			required: true,
			message: "请输入邮箱！",
			trigger: 'blur'
		}],
		password: [{
			required: true,
			message: "请输入密码！",
			trigger: 'blur'
		}],
		realname: [{
			required: true,
			message: "请输入真实姓名！",
			trigger: 'blur'
		}],
		selectedDepartment: [{
			required: true,
			message: "请选择部门！",
			trigger: "change" 
		}]
	})
	const data = ref([])
	onMounted(async () => {
		data.value = await staffHttp.getDepartment();
		console.log(data.value)
		departmentList.value = data.value.results
		console.log(departmentList.value)
	});

	const onSubmit = () => {
		formRef.value.validate(async(valid, fields) => {
			if(valid){
				try{
					await staffHttp.addStaff(staffForm.realname, staffForm.email, staffForm.password, staffForm.selectedDepartment)
					ElMessage.success('员工添加成功')
					router.push({name: 'staff_list'})
				}catch(detail){
					ElMessage.error(detail)
				}
			}
		})
	}
	
	const handleDepartmentChange = () => {
		const matchedObject = data.value.results.find(item => item.id === staffForm.selectedDepartment);
		leader_name.value = matchedObject.leader
	}
</script>

<template>
	<el-card shadow="always">
		<el-form :rules="rules" :model="staffForm" ref="formRef" label-width="80px">
			<el-form-item label="姓名" prop="realname">
				<el-input v-model="staffForm.realname" placeholder="请输入姓名">
				</el-input>
			</el-form-item>

			<el-form-item label="邮箱" prop="email">
				<el-input v-model="staffForm.email" placeholder="请输入邮箱"> </el-input>
			</el-form-item>

			<el-form-item label="密码" prop="password">
				<el-input v-model="staffForm.password" placeholder="请输入密码" type="password">
				</el-input>
			</el-form-item>

			<el-form-item label="部门" prop="selectedDepartment">
				<el-select v-model="staffForm.selectedDepartment" placeholder="请选择部门" @change="handleDepartmentChange">
					<el-option v-for="department in departmentList" :key="department.id" :label="department.name"
						:value="department.id">
					</el-option>
				</el-select>
			</el-form-item>

			<el-form-item label="领导">
				<el-input readonly disabled v-model="leader_name">
				</el-input>
			</el-form-item>

			<el-form-item>
				<el-button type="primary" @click="onSubmit"> 提交 </el-button>
			</el-form-item>
		</el-form>
	</el-card>
</template>

<style scoped></style>