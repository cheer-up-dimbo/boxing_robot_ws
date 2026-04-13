import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '@/api/client'

export const useChatStore = defineStore('chat', () => {
  const messages = ref([])
  const loaded = ref(false)
  const sending = ref(false)
  const streaming = ref(false)

  async function loadHistory() {
    if (loaded.value) return
    try {
      const history = await api.getChatHistory(50)
      messages.value = Array.isArray(history) ? history : []
    } catch (e) {
      // Start fresh if history fetch fails
    } finally {
      loaded.value = true
    }
  }

  async function sendMessage(text, image = null, depth = 'normal') {
    if ((!text && !image) || sending.value) return null

    const userMsg = {
      role: 'user',
      content: text || '',
      timestamp: new Date().toISOString(),
    }
    if (image) userMsg.image = image
    messages.value.push(userMsg)

    sending.value = true

    try {
      const response = await api.sendChatMessage(
        text || 'What is in this image?', { reply_depth: depth }, image,
      )
      const fullText = response.reply || ''
      const suggestions = response.suggestions || null
      const actions = response.actions || null
      const timestamp = response.timestamp || new Date().toISOString()

      // Add assistant message with actions immediately visible
      const assistantMsg = {
        role: 'assistant',
        content: '',
        timestamp,
        suggestions,
        actions,
      }
      messages.value.push(assistantMsg)
      const msgIdx = messages.value.length - 1

      // Reveal word by word (fast streaming)
      sending.value = false
      streaming.value = true
      const words = fullText.split(/(\s+)/)
      for (let i = 0; i < words.length; i++) {
        messages.value[msgIdx] = {
          ...messages.value[msgIdx],
          content: messages.value[msgIdx].content + words[i],
        }
        if (i < words.length - 1) {
          await new Promise(r => setTimeout(r, 20))
        }
      }
      streaming.value = false
      return messages.value[msgIdx]
    } catch (e) {
      const errorMsg = {
        role: 'assistant',
        content: 'Sorry, I could not process your request. Please try again.',
        timestamp: new Date().toISOString(),
      }
      messages.value.push(errorMsg)
      sending.value = false
      streaming.value = false
      return errorMsg
    }
  }

  function clearMessages() {
    messages.value = []
    loaded.value = false
  }

  return {
    messages,
    loaded,
    sending,
    streaming,
    loadHistory,
    sendMessage,
    clearMessages,
  }
})
