"use client"

import { useLoading } from "@/context/LoadingContext"

export default function GlobalLoader() {

  const { globalLoading } = useLoading()

  if (!globalLoading) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex justify-center items-center z-50">
      <div className="w-14 h-14 border-4 border-white border-t-transparent rounded-full animate-spin"></div>
    </div>
  )
}