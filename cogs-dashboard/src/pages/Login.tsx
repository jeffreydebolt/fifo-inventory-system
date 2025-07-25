import React, { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import AuthGuard from '../components/AuthGuard'
import supabaseClient from '../lib/supabaseClient'

const Login: React.FC = () => {
  const navigate = useNavigate()

  useEffect(() => {
    // Check if user is already logged in
    const checkUser = async () => {
      const { data: { session } } = await supabaseClient.auth.getSession()
      if (session?.user) {
        navigate('/')
      }
    }

    checkUser()

    // Listen for auth changes
    const { data: { subscription } } = supabaseClient.auth.onAuthStateChange(
      async (event, session) => {
        if (session?.user) {
          navigate('/')
        }
      }
    )

    return () => subscription.unsubscribe()
  }, [navigate])

  return (
    <AuthGuard>
      {/* This will never render since AuthGuard handles the login UI when no user */}
      <div></div>
    </AuthGuard>
  )
}

export default Login