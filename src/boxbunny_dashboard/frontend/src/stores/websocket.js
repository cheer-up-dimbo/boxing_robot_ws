import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useWebSocketStore = defineStore('websocket', () => {
  const ws = ref(null)
  const connected = ref(false)
  const lastEvent = ref(null)
  const reconnectAttempts = ref(0)
  const maxReconnectAttempts = 10
  const listeners = ref(new Map())

  let reconnectTimer = null
  let pingTimer = null

  function getWsUrl(userId, role = 'individual') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    return `${protocol}//${host}/ws?user_id=${encodeURIComponent(userId)}&role=${encodeURIComponent(role)}`
  }

  function connect(userId, role = 'individual') {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      return
    }

    const url = getWsUrl(userId, role)

    try {
      ws.value = new WebSocket(url)
    } catch (e) {
      console.error('WebSocket connection failed:', e)
      scheduleReconnect(userId, role)
      return
    }

    ws.value.onopen = () => {
      connected.value = true
      reconnectAttempts.value = 0
      startPing()
    }

    ws.value.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        lastEvent.value = message

        // Dispatch to registered listeners
        const eventListeners = listeners.value.get(message.event)
        if (eventListeners) {
          eventListeners.forEach((cb) => cb(message.data, message))
        }

        // Also dispatch to wildcard listeners
        const wildcardListeners = listeners.value.get('*')
        if (wildcardListeners) {
          wildcardListeners.forEach((cb) => cb(message.data, message))
        }
      } catch (e) {
        console.error('WebSocket message parse error:', e)
      }
    }

    ws.value.onclose = () => {
      connected.value = false
      stopPing()
      scheduleReconnect(userId, role)
    }

    ws.value.onerror = () => {
      connected.value = false
    }
  }

  function disconnect() {
    stopPing()
    clearTimeout(reconnectTimer)
    reconnectAttempts.value = 0
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
    connected.value = false
  }

  function send(event, data = {}) {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({ event, data }))
    }
  }

  function on(event, callback) {
    if (!listeners.value.has(event)) {
      listeners.value.set(event, new Set())
    }
    listeners.value.get(event).add(callback)

    // Return unsubscribe function
    return () => {
      const set = listeners.value.get(event)
      if (set) {
        set.delete(callback)
        if (set.size === 0) {
          listeners.value.delete(event)
        }
      }
    }
  }

  function scheduleReconnect(userId, role) {
    if (reconnectAttempts.value >= maxReconnectAttempts) {
      return
    }
    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.value), 30000)
    reconnectAttempts.value++
    reconnectTimer = setTimeout(() => {
      connect(userId, role)
    }, delay)
  }

  function startPing() {
    stopPing()
    pingTimer = setInterval(() => {
      send('ping')
    }, 30000)
  }

  function stopPing() {
    if (pingTimer) {
      clearInterval(pingTimer)
      pingTimer = null
    }
  }

  return {
    ws,
    connected,
    lastEvent,
    reconnectAttempts,
    connect,
    disconnect,
    send,
    on,
  }
})
