const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

// Create a simple icon with the 🛟 emoji representation
async function generateIcon() {
  const size = 512;
  const iconPath = path.join(__dirname, '../assets/icon.png');

  // Create a blue gradient background with a life preserver symbol
  const svg = `
    <svg width="${size}" height="${size}" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style="stop-color:#1e40af;stop-opacity:1" />
          <stop offset="100%" style="stop-color:#3b82f6;stop-opacity:1" />
        </linearGradient>
      </defs>
      <rect width="${size}" height="${size}" rx="64" fill="url(#bg)"/>
      <circle cx="${size/2}" cy="${size/2}" r="140" fill="none" stroke="white" stroke-width="30"/>
      <circle cx="${size/2}" cy="${size/2}" r="80" fill="none" stroke="white" stroke-width="20"/>
      <rect x="${size/2 - 15}" y="${size/2 - 140}" width="30" height="280" fill="white"/>
      <rect x="${size/2 - 140}" y="${size/2 - 15}" width="280" height="30" fill="white"/>
      <text x="${size/2}" y="${size - 80}" font-family="Arial, sans-serif" font-size="48" font-weight="bold" fill="white" text-anchor="middle">SAVIOR</text>
    </svg>
  `;

  await sharp(Buffer.from(svg))
    .resize(size, size)
    .png()
    .toFile(iconPath);

  console.log(`✅ Generated icon at: ${iconPath}`);

  // Also create a smaller tray icon
  const trayIconPath = path.join(__dirname, '../assets/tray-icon.png');
  await sharp(Buffer.from(svg))
    .resize(22, 22)
    .png()
    .toFile(trayIconPath);

  console.log(`✅ Generated tray icon at: ${trayIconPath}`);
}

generateIcon().catch(console.error);