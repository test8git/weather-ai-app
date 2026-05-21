import withPWA from "next-pwa";
/** @type {import('next').NextConfig} */

const isDev = process.env.NODE_ENV === 'development';

const nextConfig = {
  /* config options here */
  reactCompiler: true,
};

//export default nextConfig;
export default withPWA({
  dest: "public",
  register: true,
  skipWaiting: true,
  disable: isDev,
})(nextConfig);
