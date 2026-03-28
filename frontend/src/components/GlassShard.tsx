import { useRef, useMemo } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { Environment } from '@react-three/drei'
import * as THREE from 'three'

function OrbitingLight({
  color,
  intensity,
  plane,
  speed,
  radius = 3,
}: {
  color: string
  intensity: number
  plane: 'xy' | 'yz' | 'xz'
  speed: number
  radius?: number
}) {
  const ref = useRef<THREE.PointLight>(null!)

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime() * speed
    const a = Math.sin(t) * radius
    const b = Math.cos(t) * radius
    if (plane === 'xy') {
      ref.current.position.set(a, b, 0)
    } else if (plane === 'yz') {
      ref.current.position.set(0, a, b)
    } else {
      ref.current.position.set(a, 0, b)
    }
  })

  return <pointLight ref={ref} color={color} intensity={intensity} distance={10} />
}

function Shard() {
  const meshRef = useRef<THREE.Mesh>(null!)
  const targetRotation = useRef({ x: 0, y: 0 })
  const { viewport } = useThree()

  const material = useMemo(
    () =>
      new THREE.MeshPhysicalMaterial({
        transmission: 0.95,
        roughness: 0.05,
        thickness: 1.5,
        ior: 2.4,
        metalness: 0.0,
        color: new THREE.Color('#E0FB2D'),
        envMapIntensity: 1.5,
        transparent: true,
      }),
    [],
  )

  useFrame((state, delta) => {
    const mesh = meshRef.current
    if (!mesh) return

    mesh.rotation.y += 0.003
    mesh.rotation.x += 0.001

    const maxTilt = THREE.MathUtils.degToRad(15)
    const pointer = state.pointer
    const tx = (pointer.y * maxTilt * viewport.height) / viewport.height
    const ty = (pointer.x * maxTilt * viewport.width) / viewport.width
    targetRotation.current.x = tx
    targetRotation.current.y = ty

    mesh.rotation.x += (targetRotation.current.x - mesh.rotation.x) * 0.02
    mesh.rotation.y += (targetRotation.current.y - mesh.rotation.y) * 0.02

    const elapsed = state.clock.getElapsedTime()
    mesh.position.y = Math.sin(elapsed * ((2 * Math.PI) / 4)) * 0.1
  })

  return (
    <mesh ref={meshRef} material={material}>
      <icosahedronGeometry args={[0.85, 1]} />
    </mesh>
  )
}

export default function GlassShard() {
  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        zIndex: 0,
      }}
    >
      <Canvas camera={{ position: [0, 0, 6], fov: 45 }}>
        <ambientLight intensity={0.1} />
        <Shard />
        <OrbitingLight color="#E0FB2D" intensity={2} plane="xy" speed={0.5} />
        <OrbitingLight color="#FFFFFF" intensity={1.5} plane="yz" speed={0.35} />
        <OrbitingLight color="#00D4FF" intensity={1} plane="xz" speed={0.25} />
        <Environment preset="night" />
      </Canvas>
    </div>
  )
}
