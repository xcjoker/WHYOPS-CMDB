<template>
	<div class="dashboard-card">
		<div class="chart-box" ref="chartRef"></div>
		<div class="info-box">
			<div class="card-label">{{ label }}</div>
			<div class="card-value">{{ value }}</div>
		</div>
	</div>
</template>

<script setup>
	import {
		ref,
		onMounted,
		watch
	} from 'vue';
	import * as echarts from 'echarts';

	const props = defineProps({
		label: {
			type: String,
			default: ''
		},
		value: {
			type: Number,
			default: 0
		},
		color: {
			type: String,
			default: '#409EFF'
		}
	});

	const chartRef = ref(null);
	let myChart = null;

	const renderChart = () => {
		if (!chartRef.value) return;
		myChart = echarts.init(chartRef.value);

		const option = {
			series: [{
				type: 'pie',
				radius: ['70%', '90%'], // 环形
				avoidLabelOverlap: false,
				label: {
					show: false
				},
				emphasis: {
					disabled: true
				}, // 禁用鼠标悬停放大
				data: [{
						value: 1,
						itemStyle: {
							color: props.color
						}
					} // 全圆环
				]
			}]
		};
		myChart.setOption(option);
	};

	onMounted(() => {
		renderChart();
		window.addEventListener('resize', () => myChart && myChart.resize());
	});

	// 监听值变化（可选动画）
	watch(() => props.value, () => {
		// 可以在这里加数字滚动动画逻辑
	});
</script>

<style scoped>
	.dashboard-card {
		background-color: #ffffff;
		/* 白底 */
		border-radius: 4px;
		display: flex;
		align-items: center;
		padding: 15px;
		height: 90px;

		/* 加上柔和的阴影，增加层次感 */
		box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
		border: 1px solid #e4e7ed;
		/* 浅边框 */

		transition: all 0.3s;
		/* 鼠标悬停动画 */
	}

	.dashboard-card:hover {
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
		transform: translateY(-2px);
		/* 微微上浮 */
	}

	.chart-box {
		width: 60px;
		height: 60px;
		margin-right: 15px;
	}

	.info-box {
		flex: 1;
		text-align: right;
		display: flex;
		flex-direction: column;
		justify-content: center;
	}

	.card-label {
		color: #909399;
		/* 浅灰文字 */
		font-size: 13px;
		margin-bottom: 4px;
	}

	.card-value {
		color: #303133;
		/* 深黑数字 */
		font-size: 28px;
		font-weight: bold;
		font-family: 'Roboto', sans-serif;
	}
</style>