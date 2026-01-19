<template>
	<frame>
		<div class="idc-container full-height-layout">

			<div class="top-dashboard">
				<el-row :gutter="20">
					<el-col :span="6">
						<div class="stat-column">
							<el-card shadow="hover" class="stat-card">
								<template #header>
									<div class="card-header">
										<span><el-icon>
												<OfficeBuilding />
											</el-icon> 机房总数</span>
									</div>
								</template>
								<div class="stat-value">{{ tableData.length }} <span class="unit">个</span></div>
							</el-card>

							<el-card shadow="hover" class="stat-card">
								<template #header>
									<div class="card-header">
										<span><el-icon>
												<Cpu />
											</el-icon> 服务器总数</span>
									</div>
								</template>
								<div class="stat-value">{{ totalServers }} <span class="unit">台</span></div>
							</el-card>

							<el-card shadow="hover" class="stat-card info-tip">
								<div class="tip-text">
									<el-icon>
										<InfoFilled />
									</el-icon> 机房异常请及时联系管理员
								</div>
							</el-card>
						</div>
					</el-col>

					<el-col :span="18">
						<el-card shadow="never" class="map-card" :body-style="{ padding: '10px' }">
							<div id="idcMap" style="width: 100%; height: 350px;"></div>
						</el-card>
					</el-col>
				</el-row>
			</div>

			<el-card class="box-card table-card-flex" shadow="never">
				<template #header>
					<div class="card-header">
						<span class="header-title">机房详细列表</span>
						<div class="header-actions">
							<el-input v-model="search" placeholder="搜索机房地址..." :prefix-icon="Search" clearable
								style="width: 200px; margin-right: 15px;" />
							<el-button type="primary" :icon="Plus" round @click="addIdcButton">
								添加机房
							</el-button>
						</div>
					</div>
				</template>

				<el-table :data="filterTableData" stripe border style="width: 100%; height: 100%;" v-loading="loading">
					<el-table-column fixed="left" prop="机房地址" label="机房地址" min-width="200">
						<template #default="scope">
							<el-icon style="vertical-align: middle; margin-right: 5px">
								<Location />
							</el-icon>
							<span>{{ scope.row.机房地址 }}</span>
						</template>
					</el-table-column>

					<el-table-column prop="机房管理" label="机房管理员" min-width="150">
						<template #default="scope">
							<el-tag type="info" effect="plain"><el-icon>
									<User />
								</el-icon> {{ scope.row.机房管理 }}</el-tag>
						</template>
					</el-table-column>

					<el-table-column prop="机房数量" label="服务器数量" min-width="120" sortable>
						<template #default="scope">
							<el-tag :type="scope.row.机房数量 > 100 ? 'danger' : 'success'">
								{{ scope.row.机房数量 }} 台
							</el-tag>
						</template>
					</el-table-column>

<!-- 					<el-table-column label="坐标信息" min-width="160">
						<template #default="scope">
							<span v-if="scope.row.经度 && scope.row.纬度" style="font-size: 12px; color: #999;">
								E:{{scope.row.经度}}, N:{{scope.row.纬度}}
							</span>
							<el-tag v-else type="warning" size="small">无坐标</el-tag>
						</template>
					</el-table-column> -->

					<el-table-column prop="管理电话" label="联系电话" min-width="150">
						<template #default="scope">
							<el-icon>
								<Phone />
							</el-icon> {{ scope.row.管理电话 }}
						</template>
					</el-table-column>

					<el-table-column fixed="right" label="操作" width="150" align="center">
						<template v-slot="scope">
							<el-button type="primary" link :icon="Edit" @click="changeRegion(scope.row)">
								修改
							</el-button>
						</template>
					</el-table-column>
				</el-table>
			</el-card>

			<el-dialog v-model="dialogFormVisible2" title="新增机房信息" width="480px" align-center destroy-on-close>
				<el-form :model="addIdcForm" :rules="rules2" ref='formTag2' label-position="right">
					<el-form-item label="机房地址" :label-width="formLabelWidth" prop="idcRegion2">
						<el-input v-model="addIdcForm.idcRegion2" placeholder="请输入详细地址" autocomplete="off"
							:prefix-icon="Location" />
					</el-form-item>
					<el-form-item label="机房管理" :label-width="formLabelWidth" prop="idcControle2">
						<el-input v-model="addIdcForm.idcControle2" placeholder="管理员姓名" autocomplete="off"
							:prefix-icon="User" />
					</el-form-item>
					<el-form-item label="机房数量" :label-width="formLabelWidth" prop="idcCount2">
						<el-input v-model.number="addIdcForm.idcCount2" type="number" autocomplete="off" />
					</el-form-item>
					<el-form-item label="管理电话" :label-width="formLabelWidth" prop="controlPhone2">
						<el-input v-model="addIdcForm.controlPhone2" autocomplete="off" :prefix-icon="Phone" />
					</el-form-item>
				</el-form>
				<template #footer>
					<div class="dialog-footer">
						<el-button @click="dialogFormVisible2 = false">取 消</el-button>
						<el-button type="primary" :loading="btnLoading" @click="onsubmit2">确 定</el-button>
					</div>
				</template>
			</el-dialog>

			<el-dialog v-model="dialogFormVisible" title="编辑机房信息" width="480px" align-center destroy-on-close>
				<el-form :model="resetIdcRegionForm" :rules="rules" ref='formTag' label-position="right">
					<el-form-item label="机房地址" :label-width="formLabelWidth" prop="idcRegion">
						<el-input v-model="resetIdcRegionForm.idcRegion" autocomplete="off" :prefix-icon="Location" />
					</el-form-item>
					<el-form-item label="机房管理" :label-width="formLabelWidth" prop="idcControle">
						<el-input v-model="resetIdcRegionForm.idcControle" autocomplete="off" :prefix-icon="User" />
					</el-form-item>
					<el-form-item label="机房数量" :label-width="formLabelWidth" prop="idcCount">
						<el-input v-model="resetIdcRegionForm.idcCount" autocomplete="off" />
					</el-form-item>
					<el-form-item label="管理电话" :label-width="formLabelWidth" prop="controlPhone">
						<el-input v-model="resetIdcRegionForm.controlPhone" autocomplete="off" :prefix-icon="Phone" />
					</el-form-item>
				</el-form>
				<template #footer>
					<div class="dialog-footer">
						<el-button @click="dialogFormVisible = false">取 消</el-button>
						<el-button type="primary" :loading="btnLoading" @click="onsubmit">保 存</el-button>
					</div>
				</template>
			</el-dialog>
		</div>
	</frame>
</template>

<script setup>
	import {
		computed,
		onMounted,
		ref,
		reactive,
		nextTick
	} from 'vue'
	import frame from "@/views/main/frame.vue"
	import authHttp from '@/api/authHttp'
	import {
		ElMessage
	} from 'element-plus';
	import {
		Plus,
		Edit,
		Search,
		Location,
		User,
		Phone,
		OfficeBuilding,
		Cpu,
		InfoFilled
	} from '@element-plus/icons-vue'
	import * as echarts from 'echarts';
	import chinaMap from '@/assets/json/china.json'

	echarts.registerMap('china', chinaMap);

	// 状态定义
	const loading = ref(false)
	const btnLoading = ref(false)
	const search = ref('')
	const dialogFormVisible = ref(false)
	const dialogFormVisible2 = ref(false)
	const formLabelWidth = '100px'
	const tableData = ref([])
	const region_id = ref('')
	const formTag = ref()
	const formTag2 = ref()
	let myChart = null;

	// 表单对象
	let resetIdcRegionForm = reactive({
		idcRegion: '',
		idcControle: '',
		idcCount: 0,
		controlPhone: ''
	})
	let addIdcForm = reactive({
		idcRegion2: '',
		idcControle2: '',
		idcCount2: 0,
		controlPhone2: ''
	})

	// 验证规则
	const rules = reactive({
		idcRegion: [{
			required: true,
			message: '请输入机房地址',
			trigger: 'blur'
		}],
		idcControle: [{
			required: true,
			message: '请输入管理员姓名',
			trigger: 'blur'
		}],
		idcCount: [{
			required: true,
			message: '请输入数量',
			trigger: 'blur'
		}],
		controlPhone: [{
			required: true,
			message: '请输入联系电话',
			trigger: 'blur'
		}]
	});
	const rules2 = reactive({
		...rules
	}); // 复用规则

	// 计算属性
	const filterTableData = computed(() => {
		return tableData.value.filter(data =>
			!search.value ||
			data.机房地址.toLowerCase().includes(search.value.toLowerCase()) ||
			data.机房管理.toLowerCase().includes(search.value.toLowerCase())
		)
	})

	const totalServers = computed(() => {
		return tableData.value.reduce((acc, cur) => acc + cur.机房数量, 0);
	})

	// --- 核心改动：不再使用 hardcode 字典，直接使用数据 ---
	const updateMapData = () => {
		if (!myChart) return;

		const seriesData = [];
		tableData.value.forEach(item => {
			// 后端返回了 经度(longitude) 和 纬度(latitude)
			if (item.经度 && item.纬度) {
				seriesData.push({
					name: item.机房地址,
					value: [item.经度, item.纬度, item.机房数量]
				});
			}
		});

		myChart.setOption({
			series: [{
				data: seriesData
			}]
		});
	};

	const initMap = () => {
		const chartDom = document.getElementById('idcMap');
		if (!chartDom) return;
		myChart = echarts.init(chartDom);
		const option = {
			backgroundColor: '#fff',
			title: {
				text: '机房分布热力图',
				left: 'center',
				top: 10,
				textStyle: {
					color: '#333'
				}
			},
			tooltip: {
				trigger: 'item',
				formatter: params => `${params.name}<br/>服务器: ${params.value[2]} 台`
			},
			geo: {
				map: 'china',
				roam: true,
				label: {
					show: false
				},
				itemStyle: {
					areaColor: '#f3f4f6',
					borderColor: '#999'
				},
				emphasis: {
					itemStyle: {
						areaColor: '#dbeafe'
					}
				}
			},
			series: [{
				name: '机房节点',
				type: 'effectScatter',
				coordinateSystem: 'geo',
				data: [],
				symbolSize: val => Math.max(8, Math.min(val[2] / 20, 30)),
				encode: {
					value: 2
				},
				showEffectOn: 'render',
				rippleEffect: {
					brushType: 'stroke',
					scale: 3
				},
				itemStyle: {
					color: '#409EFF',
					shadowBlur: 10,
					shadowColor: '#333'
				},
				label: {
					show: true,
					position: 'right',
					formatter: '{b}',
					color: '#333'
				}
			}]
		};
		myChart.setOption(option);
		window.addEventListener('resize', () => myChart.resize());
	};

	const getList = async () => {
		loading.value = true;
		try {
			const result = await authHttp.getIdcRegion();
			// 映射后端数据到前端
			tableData.value = result.results.map(item => ({
				id: item.id,
				机房地址: item.address,
				机房管理: item.username,
				管理电话: item.username_phone,
				机房数量: item.server_count,
				// 映射经纬度
				经度: item.longitude,
				纬度: item.latitude
			}));
			nextTick(() => {
				updateMapData();
			})
		} catch (e) {
			console.error(e);
			ElMessage.error("获取数据失败");
		} finally {
			loading.value = false;
		}
	}

	// 提交逻辑 (保存后重新 getList 即可自动更新地图)
	const onsubmit = () => {
		formTag.value.validate(async (valid) => {
			if (valid) {
				btnLoading.value = true;
				try {
					await authHttp.putIdcregion(region_id.value, resetIdcRegionForm.idcRegion,
						resetIdcRegionForm.idcControle, resetIdcRegionForm.controlPhone,
						resetIdcRegionForm.idcCount)
					ElMessage.success('机房修改成功')
					dialogFormVisible.value = false
					await getList(); // 重新拉取包含最新坐标的数据
				} catch (detail) {
					ElMessage.error(typeof detail === 'string' ? detail : '修改失败')
				} finally {
					btnLoading.value = false;
				}
			}
		})
	}

	const onsubmit2 = () => {
		formTag2.value.validate(async (valid) => {
			if (valid) {
				btnLoading.value = true;
				try {
					await authHttp.addIdc(addIdcForm.idcRegion2, addIdcForm.idcControle2, addIdcForm
						.controlPhone2, addIdcForm.idcCount2)
					ElMessage.success('机房添加成功')
					dialogFormVisible2.value = false
					await getList(); // 重新拉取
				} catch (detail) {
					ElMessage.error(typeof detail === 'string' ? detail : '添加失败')
				} finally {
					btnLoading.value = false;
				}
			}
		})
	}

	const addIdcButton = () => {
		dialogFormVisible2.value = true
		Object.assign(addIdcForm, {
			idcRegion2: '',
			idcControle2: '',
			idcCount2: '',
			controlPhone2: ''
		})
		if (formTag2.value) formTag2.value.clearValidate()
	}

	const changeRegion = (row) => {
		region_id.value = row.id
		resetIdcRegionForm.idcRegion = row.机房地址
		resetIdcRegionForm.idcControle = row.机房管理
		resetIdcRegionForm.idcCount = row.机房数量
		resetIdcRegionForm.controlPhone = row.管理电话
		dialogFormVisible.value = true
		if (formTag.value) formTag.value.clearValidate()
	}

	onMounted(() => {
		getList();
		nextTick(() => {
			initMap();
		})
	})
</script>

<style scoped>
	/* 核心 Flex 布局：实现固定屏幕无滚动 */
	.idc-container {
		padding: 20px;
		height: calc(100vh - 84px);
		/* 根据你的实际顶部导航高度调整，一般在 60px - 100px 之间 */
		display: flex;
		flex-direction: column;
		box-sizing: border-box;
		overflow: hidden;
		/* 禁止最外层出滚动条 */
	}

	/* 上半部分固定 */
	.top-dashboard {
		flex-shrink: 0;
		margin-bottom: 15px;
	}

	/* 统计卡片样式 */
	.stat-column {
		display: flex;
		flex-direction: column;
		justify-content: space-between;
		height: 100%;
	}

	.stat-card {
		border-radius: 8px;
		flex: 1;
		display: flex;
		flex-direction: column;
		justify-content: center;
		margin-bottom: 10px;
	}

	.stat-card:last-child {
		margin-bottom: 0;
	}

	.card-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		font-size: 15px;
		font-weight: 500;
	}

	.stat-value {
		font-size: 24px;
		font-weight: bold;
		color: #409EFF;
		text-align: center;
	}

	.unit {
		font-size: 14px;
		color: #909399;
		font-weight: normal;
	}

	.tip-text {
		font-size: 12px;
		color: #909399;
		display: flex;
		align-items: center;
		gap: 5px;
	}

	/* 下半部分：表格卡片 Flex 自适应 */
	.table-card-flex {
		flex: 1;
		/* 关键：占据剩余高度 */
		display: flex;
		flex-direction: column;
		overflow: hidden;
		border-radius: 8px;
	}

	/* 穿透 Element 样式，让 Card Body 填满 */
	.table-card-flex :deep(.el-card__body) {
		flex: 1;
		display: flex;
		flex-direction: column;
		padding: 15px;
		height: 100%;
		overflow: hidden;
	}

	.header-title {
		font-size: 18px;
		font-weight: 600;
		color: #333;
	}

	.header-actions {
		display: flex;
		align-items: center;
	}

	.map-card {
		height: 100%;
		display: flex;
		flex-direction: column;
		justify-content: center;
	}
</style>