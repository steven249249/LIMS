/**
 * src/api/users.js
 */
import client from './client'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000/api'

export const login = (username, password) =>
  axios.post(`${API_BASE}/users/login/`, { username, password })

export const register = (data) =>
  axios.post(`${API_BASE}/users/register/`, data)

export const fetchProfile = () => client.get('/users/profile/')
export const fetchFabs = () => client.get('/users/fabs/')
export const fetchDepartments = (fabId) =>
  client.get('/users/departments/', { params: { fab_id: fabId } })
export const fetchWaferLots = (params) =>
  client.get('/users/wafer-lots/', { params })
