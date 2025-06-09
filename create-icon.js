const fs = require('fs');
const path = require('path');
const pngToIco = require('png-to-ico');

// Check if icon.png exists
try {
    fs.accessSync('icon.png', fs.constants.F_OK);
    console.log('Found icon.png, converting to icon.ico...');
    
    // Convert PNG to ICO
    pngToIco('icon.png')
        .then(buf => {
            fs.writeFileSync('icon.ico', buf);
            console.log('Successfully created icon.ico');
        })
        .catch(err => {
            console.error('Error converting icon:', err);
        });
} catch (err) {
    console.error('icon.png not found:', err.message);
} 