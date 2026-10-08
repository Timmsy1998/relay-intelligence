// A bounded incident producer for exercising the event pipeline. Requires Node 22+.
import { randomUUID } from 'node:crypto'
import { readFile } from 'node:fs/promises'
const [file, rawCount = '1'] = process.argv.slice(2)
const count = Number(rawCount)
if (!file || !Number.isInteger(count) || count < 1 || count > 100 || !process.env.RELAY_API_TOKEN) {
  console.error('Usage: RELAY_API_TOKEN=... node scripts/ingest.mjs alert.json [1..100]')
  process.exit(1)
}
const payload = JSON.parse(await readFile(file, 'utf8'))
const base = process.env.RELAY_API_URL || 'http://localhost:8000'
for (let i = 0; i < count; i++) {
  const key = randomUUID() // Reused if this request needs a retry.
  let delivered = false
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const response = await fetch(`${base}/api/incidents/`, {
        method: 'POST', signal: AbortSignal.timeout(15000),
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${process.env.RELAY_API_TOKEN}`, 'Idempotency-Key': key },
        body: JSON.stringify(payload),
      })
      if (response.status >= 500) throw new Error(`Server error ${response.status}`)
      if (!response.ok) throw Object.assign(new Error(`Submission rejected (${response.status})`), { permanent: true })
      const incident = await response.json()
      console.log(JSON.stringify({ incident_id: incident.id, status: incident.status }))
      delivered = true; break
    } catch (error) {
      if (error.permanent || attempt === 2) throw error
      await new Promise(resolve => setTimeout(resolve, 500 * (2 ** attempt)))
    }
  }
  if (!delivered) process.exitCode = 1
}
