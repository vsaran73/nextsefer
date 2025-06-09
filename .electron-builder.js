const path = require('path');
const { Platform } = require('electron-builder');

module.exports = {
  appId: 'com.nextsefer.app',
  productName: 'NextSefer',
  files: [
    '**/*',
    'build/**/*',
    '!**/node_modules/*/{CHANGELOG.md,README.md,README,readme.md,readme}',
    '!**/node_modules/*/{test,__tests__,tests,powered-test,example,examples}',
    '!**/node_modules/*.d.ts',
    '!**/node_modules/.bin',
    '!**/*.{iml,o,hprof,orig,pyc,pyo,rbc,swp,csproj,sln,xproj}',
    '!.editorconfig',
    '!**/._*',
    '!**/{.DS_Store,.git,.hg,.svn,CVS,RCS,SCCS,.gitignore,.gitattributes}',
    '!**/{__pycache__,thumbs.db,.flowconfig,.idea,.vs,.nyc_output}',
    '!**/{appveyor.yml,.travis.yml,circle.yml}',
    '!**/{npm-debug.log,yarn.lock,.yarn-integrity,.yarn-metadata.json}'
  ],
  extraResources: [
    {
      from: 'python_dist',
      to: 'python_dist',
      filter: ['**/*']
    },
    {
      from: 'NextSefer.bat',
      to: 'NextSefer.bat'
    }
  ],
  directories: {
    buildResources: 'build',
    output: 'dist'
  },
  artifactName: '${productName}-Setup-${version}.${ext}',
  win: {
    target: ['nsis'],
    icon: 'icon.ico',
  },
  nsis: {
    oneClick: false,
    allowToChangeInstallationDirectory: true,
    installerIcon: 'icon.ico',
    uninstallerIcon: 'icon.ico',
    installerHeaderIcon: 'icon.ico',
    createDesktopShortcut: true,
    createStartMenuShortcut: true,
    shortcutName: 'NextSefer',
    include: 'installer.nsh'
  },
  mac: {
    target: ['dmg'],
    icon: 'icon.png',
  },
  linux: {
    target: ['AppImage'],
    icon: 'icon.png',
    category: 'Office',
  }
}; 