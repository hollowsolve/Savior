const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');

const isDev = process.env.NODE_ENV === 'development';

module.exports = [
  // Main process config
  {
    mode: isDev ? 'development' : 'production',
    entry: './electron/main.ts',
    target: 'electron-main',
    module: {
      rules: [
        {
          test: /\.ts$/,
          use: 'ts-loader',
          exclude: /node_modules/
        }
      ]
    },
    resolve: {
      extensions: ['.ts', '.js']
    },
    output: {
      path: path.resolve(__dirname, 'dist'),
      filename: 'main.js'
    }
  },
  // Preload script config
  {
    mode: isDev ? 'development' : 'production',
    entry: './electron/preload.ts',
    target: 'electron-preload',
    module: {
      rules: [
        {
          test: /\.ts$/,
          use: 'ts-loader',
          exclude: /node_modules/
        }
      ]
    },
    resolve: {
      extensions: ['.ts', '.js']
    },
    output: {
      path: path.resolve(__dirname, 'dist'),
      filename: 'preload.js'
    }
  },
  // Renderer process config (React app)
  {
    mode: isDev ? 'development' : 'production',
    entry: './src/index.tsx',
    target: 'web', // Change from electron-renderer to web for browser compatibility
    devtool: isDev ? 'inline-source-map' : false,
    module: {
      rules: [
        {
          test: /\.tsx?$/,
          use: 'ts-loader',
          exclude: /node_modules/
        },
        {
          test: /\.css$/,
          use: ['style-loader', 'css-loader', 'postcss-loader']
        },
        {
          test: /\.(png|jpg|gif|svg)$/,
          type: 'asset/resource'
        }
      ]
    },
    resolve: {
      extensions: ['.tsx', '.ts', '.js', '.jsx'],
      alias: {
        '@': path.resolve(__dirname, 'src'),
        '@electron': path.resolve(__dirname, 'electron'),
        '@shared': path.resolve(__dirname, 'shared')
      },
      fallback: {
        "events": require.resolve("events/"),
        "path": require.resolve("path-browserify"),
        "fs": false,
        "child_process": false,
        "os": false
      }
    },
    output: {
      path: path.resolve(__dirname, 'dist'),
      filename: 'renderer.js'
    },
    plugins: [
      new HtmlWebpackPlugin({
        template: './public/index.html'
      })
    ],
    devServer: {
      port: 3000,
      hot: true,
      historyApiFallback: true
    }
  }
];