/**
 * src/router/index.js – Vue Router with role-based guards.
 */
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

import LoginView from '../views/LoginView.vue'
import DashboardView from '../views/DashboardView.vue'
import OrderCreateView from '../views/requester/OrderCreateView.vue'
import OrderListView from '../views/requester/OrderListView.vue'
import OrderReviewView from '../views/manager/OrderReviewView.vue'
import OrderTasksView from '../views/member/OrderTasksView.vue'
import EquipmentDashboardView from '../views/EquipmentDashboardView.vue'

import AdminLayout from '../views/admin/AdminLayout.vue'
import AdminDashboardView from '../views/admin/DashboardView.vue'
import AdminActivityLogsView from '../views/admin/ActivityLogsView.vue'
import AdminFabsView from '../views/admin/FabsView.vue'
import AdminDepartmentsView from '../views/admin/DepartmentsView.vue'
import AdminWaferLotsView from '../views/admin/WaferLotsView.vue'
import AdminUsersView from '../views/admin/UsersView.vue'
import AdminExperimentsView from '../views/admin/ExperimentsView.vue'
import AdminEquipmentTypesView from '../views/admin/EquipmentTypesView.vue'
import AdminEquipmentView from '../views/admin/EquipmentView.vue'
import AdminExperimentRequirementsView from '../views/admin/ExperimentRequirementsView.vue'
import AdminOrdersView from '../views/admin/OrdersView.vue'
import AdminOrderStagesView from '../views/admin/OrderStagesView.vue'
import AdminBookingsView from '../views/admin/BookingsView.vue'

const routes = [
  { path: '/login', name: 'Login', component: LoginView, meta: { guest: true } },
  { path: '/', name: 'Dashboard', component: DashboardView },
  // Requester
  { path: '/orders', name: 'MyOrders', component: OrderListView },
  { path: '/orders/create', name: 'CreateOrder', component: OrderCreateView },
  // Lab Manager
  {
    path: '/orders/review',
    name: 'ReviewOrders',
    component: OrderReviewView,
    meta: { roles: ['lab_manager', 'superuser'] },
  },
  // Lab Member
  {
    path: '/orders/tasks',
    name: 'LabTasks',
    component: OrderTasksView,
    meta: { roles: ['lab_member', 'lab_manager', 'superuser'] },
  },
  // Equipment dashboard — hidden from regular employees / lab members; the
  // requester UI must not surface the underlying machine inventory.
  {
    path: '/equipment',
    name: 'EquipmentDashboard',
    component: EquipmentDashboardView,
    meta: { roles: ['lab_manager', 'superuser'] },
  },

  // Admin (superuser only)
  {
    path: '/admin',
    component: AdminLayout,
    meta: { roles: ['superuser'] },
    children: [
      { path: '', redirect: '/admin/dashboard' },
      { path: 'dashboard', name: 'AdminDashboard', component: AdminDashboardView },
      { path: 'logs', name: 'AdminLogs', component: AdminActivityLogsView },
      { path: 'fabs', name: 'AdminFabs', component: AdminFabsView },
      { path: 'departments', name: 'AdminDepartments', component: AdminDepartmentsView },
      { path: 'wafer-lots', name: 'AdminWaferLots', component: AdminWaferLotsView },
      { path: 'users', name: 'AdminUsers', component: AdminUsersView },
      { path: 'experiments', name: 'AdminExperiments', component: AdminExperimentsView },
      { path: 'equipment-types', name: 'AdminEquipmentTypes', component: AdminEquipmentTypesView },
      { path: 'equipment', name: 'AdminEquipment', component: AdminEquipmentView },
      {
        path: 'experiment-requirements',
        name: 'AdminExperimentRequirements',
        component: AdminExperimentRequirementsView,
      },
      { path: 'orders', name: 'AdminOrders', component: AdminOrdersView },
      { path: 'order-stages', name: 'AdminOrderStages', component: AdminOrderStagesView },
      { path: 'bookings', name: 'AdminBookings', component: AdminBookingsView },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to, from, next) => {
  const auth = useAuthStore()

  if (auth.accessToken && !auth.user) {
    await auth.loadProfile()
  }

  if (to.meta.guest) {
    return auth.isLoggedIn ? next('/') : next()
  }

  if (!auth.isLoggedIn) {
    return next('/login')
  }

  if (to.meta.roles && !to.meta.roles.includes(auth.role)) {
    return next('/')
  }

  next()
})

export default router
