let audioContext: AudioContext | null = null

function getAudioContext() {
  const Context = window.AudioContext
  if (!Context) return null
  audioContext ??= new Context()
  return audioContext
}

export async function unlockNotificationSound() {
  const context = getAudioContext()
  if (context?.state === 'suspended') await context.resume()
}

export async function playNotificationSound(soundCode = 'CHIME', volumePercent = 70) {
  const context = getAudioContext()
  if (!context) return
  if (context.state === 'suspended') await context.resume()
  if (context.state !== 'running') return
  const oscillator = context.createOscillator()
  const gain = context.createGain()
  oscillator.type = soundCode === 'ALERT' ? 'square' : soundCode === 'SOFT' ? 'sine' : 'triangle'
  oscillator.frequency.setValueAtTime(soundCode === 'BELL' ? 1100 : soundCode === 'SOFT' ? 520 : soundCode === 'ALERT' ? 740 : 880, context.currentTime)
  gain.gain.setValueAtTime(0.0001, context.currentTime)
  gain.gain.exponentialRampToValueAtTime(Math.max(0.0001, 0.18 * volumePercent / 100), context.currentTime + 0.02)
  gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 0.22)
  oscillator.connect(gain)
  gain.connect(context.destination)
  oscillator.start()
  oscillator.stop(context.currentTime + 0.24)
}
