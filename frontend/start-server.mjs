import { createServer } from 'vite';

async function start() {
  const server = await createServer({
    configFile: './vite.config.ts',
    server: {
      port: 5173,
      host: '0.0.0.0',
    },
  });
  await server.listen();
  server.printUrls();
  
  // Keep process alive indefinitely
  setInterval(() => {}, 1 << 30);
}

start().catch((err) => {
  console.error('Failed to start Vite server:', err);
  process.exit(1);
});
