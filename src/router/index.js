import {
	createRouter,
	createWebHashHistory
} from 'vue-router'
import login from "@/views/login/login.vue"
import frame from "@/views/main/frame.vue"
import IdcRegion from "@/views/idc/IdcRegion.vue"
import idcServer from "@/views/idc/IdcServer.vue"
import {
	useAuthStore
} from '@/stores/auth'
import publish from "@/views/inform/publish.vue"
import inform_detail from "@/views/inform/detail.vue"
import inform_list from "@/views/inform/list.vue"
import web from "@/views/web/web.vue"
import monitor from "@/views/web/monitor.vue"
import webssh from "@/views/web/xterm.vue"
import staffadd from  "@/views/staff/add.vue"
import stafflist from  "@/views/staff/list.vue"
import home from "@/views/home/home.vue"
import clusterInfo from "@/views/cluster/clusterInfo.vue"
import clusterCreate from "@/views/cluster/clusterCreate.vue"
import clusterDashboard from "@/views/cluster/clusterDashboard.vue"
import dashboardCard from "@/views/cluster/dashboardCard.vue"
import podInfo from "@/views/cluster/podInfo.vue"
import deploymentInfo from "@/views/cluster/deploymentInfo.vue"
import statefulsetInfo from "@/views/cluster/statefulsetInfo.vue"
import daemonsetInfo from "@/views/cluster/daemonsetInfo.vue"
import jobInfo from "@/views/cluster/jobInfo.vue"
import cronjobInfo from "@/views/cluster/cronjobInfo.vue"
import pvInfo from "@/views/storage/pvInfo.vue"
import pvcInfo from "@/views/storage/pvcInfo.vue"
import storageclassInfo from "@/views/storage/storageclassInfo.vue"
import serviceInfo from "@/views/network/serviceInfo.vue"
import ingressInfo from "@/views/network/ingressInfo.vue"


const router = createRouter({
	history: createWebHashHistory(import.meta.env.BASE_URL),
	routes: [{
			path: '/',
			name: 'frame',
			component: frame,
			children: [
			{
				path: '/',
				name: 'home',
				component: home,
			}, {
				path: '/inform/publish',
				name: 'inform_publish',
				component: publish,
			}, {
				path: '/inform/list',
				name: 'inform_list',
				component: inform_list,
			}, {
				path: '/inform/detail/:pk',
				name: 'inform_detail',
				component: inform_detail,
			},
			{
				path: '/staff/add',
				name: 'staff_add',
				component: staffadd
			},
			{
				path: '/staff/list',
				name: 'staff_list',
				component: stafflist
			}]
		},
		{
			path: '/login',
			name: 'login',
			component: login
		},
		{
			path: '/idc', // 父路径
			children: [{
				path: 'region',
				name: 'region',
				component: IdcRegion,
			}, {
				path: 'server',
				name: 'server',
				component: idcServer,
			}]
		},
		{
			path: '/web',
			name: 'web',
			component: web
		},
		{
			path: '/monitor/:ip',
			name: 'monitor',
			component: monitor,
			props: route => ({
				ip: route.params.ip
			}) // 从 route.params 中获取 ip 参数
		},
		{
			path: '/webssh',
			name: 'webssh',
			component: webssh
		},
		{
			path: '/cluster', // 父路径
			children: [{
				path: 'info',
				name: 'info',
				component: clusterInfo,
			}, {
				path: 'create',
				name: 'create',
				component: clusterCreate,
			}, {
				path: 'detailView/:id',
				name: 'detailView',
				component: clusterDashboard
			}]
		},
		{
			path: '/workload', // 父路径
			children: [{
				path: 'pod',
				name: 'pod',
				component: podInfo,
			},{
				path: 'deployment',
				name: 'deployment',
				component: deploymentInfo,
			},{
				path: 'statefulset',
				name: 'statefulset',
				component: statefulsetInfo
			},{
				path: 'daemonset',
				name: 'daemonset',
				component: daemonsetInfo
			},{
				path: 'job',
				name: 'job',
				component: jobInfo
			},{
				path: 'cronjob',
				name: 'cronjob',
				component: cronjobInfo
			}]
		},
		{
			path: '/storage', // 父路径
			children: [{
				path: 'pv',
				name: 'pv',
				component: pvInfo,
			},{
				path: 'pvc',
				name: 'pvc',
				component: pvcInfo,
			},{
				path: 'storageclass',
				name: 'storageclass',
				component: storageclassInfo,
			},]
		},
		{
			path: '/network', // 父路径
			children: [{
				path: 'service',
				name: 'service',
				component: serviceInfo,
			},{
				path: 'ingress',
				name: 'ingress',
				component: ingressInfo,
			},]
		},


	]
})

router.beforeEach((to, from) => {
	const authStore = useAuthStore()
	if (!authStore.is_logined && to.name != 'login') {
		return {
			name: 'login'
		}
	}

})

export default router