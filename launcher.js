const fs = require('node:fs')
const http = require('node:http')
const net = require('node:net')
const path = require('node:path')
const { spawn, spawnSync } = require('node:child_process')

const projectRoot = __dirname
const pythonExe = path.join(projectRoot, '.venv', 'Scripts', 'python.exe')
const frontendRoot = path.join(projectRoot, 'frontend')
const viteScript = path.join(frontendRoot, 'node_modules', 'vite', 'bin', 'vite.js')
const ownedChildren = []
const checkOnly = process.argv.includes('--check-startup')
let stopping = false
const logDir = path.join(projectRoot, 'logs')
fs.mkdirSync(logDir, { recursive: true })
const logFile = path.join(logDir, 'startup-' + Date.now() + '-' + process.pid + '.log')

function log(message) {
  console.log(message)
  fs.appendFileSync(logFile, message + '\n')
}

function runChecked(command, args) {
  const result = spawnSync(command, args, {
    cwd: projectRoot,
    env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
    encoding: 'utf8', windowsHide: true,
  })
  if (result.stdout) log(result.stdout.trimEnd())
  if (result.stderr) log(result.stderr.trimEnd())
  if (result.error) throw result.error
  if (result.status !== 0) throw new Error(path.basename(command) + ' exited with code ' + result.status)
}

// A failed connection does not mean a port is free: test binding instead.
function canBind(port) {
  return new Promise((resolve, reject) => {
    const server = net.createServer()
    server.once('error', (error) => {
      if (['EADDRINUSE', 'EACCES'].includes(error.code)) resolve(false)
      else reject(error)
    })
    server.listen({ host: '127.0.0.1', port, exclusive: true }, () => {
      server.close(() => resolve(true))
    })
  })
}

async function selectPort(first) {
  for (let port = first; port < first + 20; port++) {
    if (await canBind(port)) return port
    log('Port ' + port + ' is occupied or unavailable; checking the next port.')
  }
  throw new Error('No available port between ' + first + ' and ' + (first + 19))
}

function probe(endpoint) {
  return new Promise((resolve) => {
    let settled = false
    const finish = (ok, detail) => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      resolve({ ...endpoint, ok, detail })
    }
    const req = http.get(endpoint.url, { agent: false, headers: { Accept: '*/*' } }, (res) => {
      let body = ''
      res.setEncoding('utf8')
      res.on('data', (chunk) => { body += chunk })
      res.on('error', (error) => finish(false, error.code || error.message))
      res.on('end', () => {
        if (res.statusCode !== 200) return finish(false, 'HTTP ' + res.statusCode)
        if (endpoint.kind === 'api') {
          try {
            const data = JSON.parse(body)
            const valid = data.service === 'campus-loop-api' && data.status === 'ok' && data.edition === 'items-only-v1' && data.capabilities?.includes('category-suggestion-hybrid-v3')
            return finish(valid, valid ? 'HTTP 200; Campus Loop API' : 'HTTP 200; unexpected API')
          } catch {
            return finish(false, 'Response is not API JSON')
          }
        }
        const valid = body.includes('Campus Loop') && body.includes('/src/main.js')
        finish(valid, valid ? 'HTTP 200; Campus Loop page' : 'HTTP 200; unexpected page')
      })
    })
    const timer = setTimeout(() => req.destroy(new Error('Request timed out after 5 seconds')), 5000)
    req.on('error', (error) => finish(false, error.code || error.message))
  })
}

async function waitUntilReady(endpoints) {
  const deadline = Date.now() + 60000
  let previous = ''
  let states = []
  while (Date.now() < deadline) {
    states = await Promise.all(endpoints.map(probe))
    const summary = states.map((s) => s.label + ': ' + (s.ok ? 'OK' : 'WAIT') + ' (' + s.detail + ')').join(' | ')
    if (summary !== previous) log(summary)
    previous = summary
    if (states.every((s) => s.ok)) return
    await new Promise((resolve) => setTimeout(resolve, 500))
  }
  throw new Error('Startup timed out:\n' + states.filter((s) => !s.ok)
    .map((s) => '  ' + s.label + ': ' + s.url + ' -> ' + s.detail).join('\n'))
}

function startOwned(label, command, args, cwd, extraEnv = {}) {
  const child = spawn(command, args, {
    cwd, env: { ...process.env, ...extraEnv },
    stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true,
  })
  ownedChildren.push(child)
  for (const stream of [child.stdout, child.stderr]) {
    stream.on('data', (chunk) => {
      process.stdout.write(chunk)
      fs.appendFileSync(logFile, chunk)
    })
  }
  child.once('error', (error) => {
    log('[PROCESS ERROR] ' + label + ': ' + error.message)
    stopOwnedChildren(1)
  })
  child.once('exit', (code, signal) => {
    if (!stopping) {
      log('[PROCESS EXIT] ' + label + ': ' + (signal || 'code ' + code) + '. Log: ' + logFile)
      stopOwnedChildren(1)
    }
  })
}

function stopOwnedChildren(exitCode) {
  if (stopping) return
  stopping = true
  for (const child of ownedChildren) {
    if (child.exitCode === null && !child.killed) child.kill()
  }
  setTimeout(() => process.exit(exitCode), 500)
}

async function main() {
  log('Node: ' + process.version + ' (' + process.execPath + ')')
  log('Startup log: ' + logFile)
  if (!fs.existsSync(pythonExe)) throw new Error('Python virtual environment not found: ' + pythonExe)
  if (!fs.existsSync(viteScript)) throw new Error('Frontend dependencies not found: ' + viteScript)
  log('Checking Python dependencies...')
  runChecked(pythonExe, ['-m', 'pip', 'check'])
  log('Initializing the database...')
  runChecked(pythonExe, ['init_db.py'])

  let backendPort = 5000
  const existing = await probe({ url: 'http://127.0.0.1:5000/api/v1/health', kind: 'api' })
  if (existing.ok) {
    log('Using the existing Campus Loop backend on port 5000.')
  } else {
    backendPort = await selectPort(5000)
    log('Starting Flask backend on port ' + backendPort + '...')
    startOwned('Backend', pythonExe, ['run.py'], projectRoot, {
      HOST: '127.0.0.1', PORT: String(backendPort), FLASK_DEBUG: '0',
      PYTHONUNBUFFERED: '1', PYTHONIOENCODING: 'utf-8',
    })
  }
  const backendUrl = 'http://127.0.0.1:' + backendPort
  const frontendPort = await selectPort(3000)
  const frontendUrl = 'http://127.0.0.1:' + frontendPort
  log('Starting Vue frontend: ' + frontendUrl)
  startOwned('Frontend', process.execPath,
    [viteScript, '--host', '127.0.0.1', '--port', String(frontendPort), '--strictPort', '--clearScreen', 'false'],
    frontendRoot, { VITE_API_TARGET: backendUrl })

  await waitUntilReady([
    { label: 'Backend', url: backendUrl + '/api/v1/health', kind: 'api' },
    { label: 'Frontend', url: frontendUrl + '/', kind: 'page' },
    { label: 'API proxy', url: frontendUrl + '/api/v1/health', kind: 'api' },
  ])
  log('\nCampus Loop started successfully.\nFrontend: ' + frontendUrl + '\nBackend:  ' + backendUrl)
  if (checkOnly) {
    log('Startup check passed. Stopping only the processes started by this check.')
    stopOwnedChildren(0)
    return
  }
  if (!process.argv.includes('--no-browser')) {
    const browser = spawn('cmd.exe', ['/d', '/c', 'start', '', frontendUrl], {
      detached: true, stdio: 'ignore', windowsHide: true,
    })
    browser.on('error', () => log('Please open ' + frontendUrl + ' in your browser.'))
    browser.unref()
  }
  log('Keep this window open. Press Ctrl+C to stop the services started here.')
}

process.on('SIGINT', () => stopOwnedChildren(0))
process.on('SIGTERM', () => stopOwnedChildren(0))
main().catch((error) => {
  log('\n[STARTUP FAILED] ' + error.message + '\nFull log: ' + logFile)
  stopOwnedChildren(1)
})
