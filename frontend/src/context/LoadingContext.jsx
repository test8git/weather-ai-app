"use client"

import { createContext, useContext, useState } from "react"

const LoadingContext = createContext()

export function LoadingProvider({ children }) {

  const [globalLoading, setGlobalLoading] = useState(false)

  return (

    <LoadingContext.Provider
      value={{
        globalLoading,
        setGlobalLoading
      }}
    >

      {children}

    </LoadingContext.Provider>

  )
}

export function useLoading() {
  return useContext(LoadingContext)
}