<template>
	<div class="inform-container">
		<el-card class="box-card" shadow="never">
			<template #header>
				<div class="card-header">
					<span class="header-title">
						<el-icon class="header-icon">
							<BellFilled />
						</el-icon>通知公告
					</span>
					<div class="header-actions">
						<el-button :icon="Refresh" circle @click="fetchData" />
					</div>
				</div>
			</template>

			<el-table :data="informs" stripe style="width: 100%" v-loading="loading" element-loading-text="加载通知中..."
				:header-cell-style="{background:'#f5f7fa', color:'#606266'}">
				<el-table-column label="通知标题" min-width="200" show-overflow-tooltip>
					<template #default="scope">
						<div class="title-wrapper">
							<el-badge :is-dot="scope.row.reads.length === 0" class="item-badge">
								<el-icon v-if="scope.row.reads.length === 0" color="#F56C6C"
									style="margin-right: 4px; vertical-align: -2px;">
									<Message />
								</el-icon>
								<el-icon v-else color="#909399" style="margin-right: 4px; vertical-align: -2px;">
									<Postcard />
								</el-icon>
							</el-badge>

							<RouterLink :to="{ name: 'inform_detail', params: { pk: scope.row.id } }"
								class="inform-link" :class="{ 'unread': scope.row.reads.length === 0 }">
								{{ scope.row.title }}
							</RouterLink>
						</div>
					</template>
				</el-table-column>

				<el-table-column label="发布者" min-width="150">
					<template #default="scope">
						<div class="author-info">
							<el-tag size="small" effect="plain"
								type="info">{{ scope.row.author.department.name }}</el-tag>
							<span class="author-name">{{ scope.row.author.realname }}</span>
						</div>
					</template>
				</el-table-column>

				<el-table-column label="发布时间" width="180">
					<template #default="scope">
						<span style="color: #909399; display: flex; align-items: center;">
							<el-icon style="margin-right: 4px;">
								<Clock />
							</el-icon>
							{{ timeFormatter.stringFromDateTime(scope.row.create_time) }}
						</span>
					</template>
				</el-table-column>

				<el-table-column label="操作" width="100" align="center" fixed="right">
					<template #default="scope">
						<el-tooltip v-if="scope.row.author.uid == authStore.user.uid" content="删除通知" placement="top">
							<el-button @click="onDeletInform(scope.row)" type="danger" link
								:icon="Delete">删除</el-button>
						</el-tooltip>
					</template>
				</el-table-column>
			</el-table>

			<div class="footer-pagination">
				<OAPagination v-model="pagination.page" :total="pagination.total"></OAPagination>
			</div>
		</el-card>
	</div>
</template>

<script setup name='listinform'>
	import {
		ref,
		reactive,
		onMounted,
		watch
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
	import {
		Delete,
		BellFilled,
		Message,
		Postcard,
		Clock,
		Refresh
	} from '@element-plus/icons-vue' // 记得引入图标

	const authStore = useAuthStore()
	const loading = ref(false)
	let informs = ref([])

	// 修正 typo: totle -> total
	let pagination = reactive({
		page: 1,
		total: 0
	})

	// 封装获取数据的方法
	const fetchData = async () => {
		loading.value = true
		try {
			// 传入当前的页码
			let data = await informHttp.getInformList(pagination.page)
			pagination.total = data.count
			informs.value = data.results
		} catch (detail) {
			ElMessage.error(typeof detail === 'string' ? detail : '获取列表失败')
		} finally {
			loading.value = false
		}
	}

	const onDeletInform = async (row) => {
		try {
			await ElMessageBox.confirm(
				`确定要删除通知 "${row.title}" 吗?`,
				'警告', {
					confirmButtonText: '确定删除',
					cancelButtonText: '取消',
					type: 'warning',
					icon: Delete, // 弹窗加个图标
					draggable: true
				}
			)
			loading.value = true
			await informHttp.deleteInform(row.id)
			ElMessage.success('通知删除成功')

			// 删除成功后，重新获取当前页数据（如果当前页只有一条且被删了，逻辑上可能需要处理回退页码，这里暂简易处理）
			await fetchData()
		} catch (error) {
			if (error !== 'cancel') {
				ElMessage.info('删除操作已取消')
			}
		} finally {
			loading.value = false
		}
	}

	// 监听分页变化，自动刷新数据
	watch(() => pagination.page, () => {
		fetchData()
	})

	onMounted(() => {
		fetchData()
	})
</script>

<style scoped>
	.inform-container {
		/* 如果外部没有 padding，这里可以加 */
		/* padding: 20px; */
	}

	.box-card {
		border-radius: 8px;
	}

	.card-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.header-title {
		font-size: 18px;
		font-weight: 600;
		color: #303133;
		display: flex;
		align-items: center;
	}

	.header-icon {
		margin-right: 8px;
		color: #409EFF;
	}

	/* 标题链接样式 */
	.title-wrapper {
		display: flex;
		align-items: center;
	}

	.inform-link {
		text-decoration: none;
		color: #606266;
		transition: color 0.3s;
		margin-left: 5px;
		display: inline-block;
		max-width: 100%;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.inform-link:hover {
		color: #409EFF;
	}

	/* 未读消息加粗 */
	.inform-link.unread {
		font-weight: 600;
		color: #303133;
	}

	.item-badge {
		/* 调整红点位置 */
		margin-right: 0;
		display: flex;
		align-items: center;
	}

	/* 发布者样式 */
	.author-info {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.author-name {
		font-weight: 500;
		color: #606266;
	}

	.footer-pagination {
		margin-top: 20px;
		display: flex;
		justify-content: flex-end;
	}

	/* 覆盖 el-badge 的默认样式，让它不要把内容挤偏 */
	:deep(.el-badge__content.is-fixed) {
		top: 2px;
		right: 2px;
	}
</style>