# This script was generated by OpenMM-Setup on 2021-07-22.
# NPT for determine the inital box size for the NVT runs


import sys
from simtk.openmm import *
from simtk.openmm.app import *
from simtk.unit import *
import numpy as np

#OpenMM Plugin Imports
# https://github.com/z-gong/openmm-velocityVerlet
from velocityverletplugin import VVIntegrator


#extra stuff from VVplugin repo
sys.path.append("/home/eduard/openmm_plugins/openmm-velocityVerlet/examples/")
from ommhelper import DrudeTemperatureReporter, ViscosityReporter



file_base, temp, t_incr, step_number, w_freq = np.loadtxt("./myjob.def", dtype=str, usecols=1, unpack=False)
print(file_base, temp, step_number, t_incr, w_freq)

Temp= float(temp)
steps= int(step_number)  # 0.5fm*50000=25ps 
t_increment=float(t_incr)
write_freq= int(w_freq)


#Counting number for divided trajectories
cnt = int(sys.argv[1])
pcnt = cnt-1



if cnt > 1:
    rst = f'traj/npt_{pcnt}.rst'  #restart file 



# Input Files
#file_base = sys.argv[2]
psf = CharmmPsfFile(f"{file_base}.psf")
crd = CharmmCrdFile(f"{file_base}.crd")
#crd = PDBFile("mini.pdb")
para_files = [ "mod_toppar_drude_model_2018c.str", "mod_toppar_drude_master_protein_2018f.str","%s_ntf2_0.4_ED.str"%(file_base)]
params = CharmmParameterSet(*[f"{para_file}" for para_file in para_files])



# System Configuration
print("System Configuration")
nonbondedMethod = PME
nonbondedCutoff = 1.2*nanometers
ewaldErrorTolerance = 0.0005
constraints = HBonds
constraintTolerance = 0.000001



# Integration Options
print("Integration Options")

if cnt ==1:      
    dt = 0.00005*picoseconds
elif cnt ==2:    
    dt = 0.0001*picoseconds
else:            
    dt = 0.0005*picoseconds
                 
#dt = t_increment*picoseconds          #timestep 0.5 fs typical for pol. sim.

temperature = Temp*kelvin
d_temperature = 1*kelvin

pressure = 1.0*atmospheres      
barostatInterval = 25

coll_freq = 10.0/picosecond      #the frequency of the interaction with the heat bath  
d_coll_freq = 100.0/picosecond

drude_hardwall = 0.2




# Simulation Options
print("Simulation Options")

#define used Platform CUDA CPU OPENCL
platform = Platform.getPlatformByName('CUDA')
platformProperties = {'Precision': 'mixed'}
print(platform.getName())


xtl = 65.0*angstroms
psf.setBox(xtl,xtl,xtl)
topology = psf.topology
positions = crd.positions
system = psf.createSystem(params, nonbondedMethod=nonbondedMethod, nonbondedCutoff=nonbondedCutoff, constraints=constraints, ewaldErrorTolerance=ewaldErrorTolerance)


#Barostat for npt
system.addForce(MonteCarloBarostat(pressure, temperature, barostatInterval))



# Integrator
#integrator = VVIntegrator(temperature*kelvin, coll_freq/picosecond, d_temperature*kelvin, d_coll_freq/picosecond, dt*picoseconds)
integrator = VVIntegrator(temperature, coll_freq, d_temperature, d_coll_freq, dt)  #test to check the dimension implications

#integrator = DrudeLangevinIntegrator(temperature*kelvin, coll_freq/picosecond, d_temperature*kelvin, d_coll_freq/picosecond, dt*picoseconds)

#integrator = NoseHooverIntegrator(temperature, coll_freq, dt)
#This is an Integrator which simulates a System using one or more Nose Hoover chain thermostats, using the "middle" leapfrog propagation algorithm described in J. Phys. Chem. A 2019, 123, 6056-6079.

#integrator = DrudeNoseHooverIntegrator(temperature*kelvin, coll_freq/picosecond, d_temperature*kelvin, d_coll_freq/picosecond, dt*picoseconds)


integrator.setConstraintTolerance(constraintTolerance)



#Drude hard wall
integrator.setMaxDrudeDistance(drude_hardwall*angstroms)
if integrator.getMaxDrudeDistance() == 0:
    print("No Drude Hard Wall Contraint in use")
else:
    print("Drude Hard Wall set to {}".format(integrator.getMaxDrudeDistance()))



# Prepare the Simulation
simulation = Simulation(topology, system, integrator, platform, platformProperties)
simulation.context.setPositions(positions)

print('Building system...')

if cnt > 1:
    with open(rst, 'r') as f:
        simulation.context.setState(XmlSerializer.deserialize(f.read()))

if cnt == 1: #minimize
    print('Performing energy minimization...')
    simulation.minimizeEnergy(maxIterations=5000)
    print(simulation.context.getState(getEnergy=True).getPotentialEnergy())
    print("Saving minimized pdb...")
    positions = simulation.context.getState(getPositions=True).getPositions()
    simulation.context.setVelocitiesToTemperature(temperature)
    PDBFile.writeFile(simulation.topology, positions, open("mini.pdb",'w'))
    


# simulate 
#steps = 4000000                           # 0.5fm*400000=200ps=0.2ns
#steps= int(step_number)  #50000           # 0.5fm*50000=25ps   
#write_freq= int(w_freq)
dcdReporter = DCDReporter(f"traj/npt_{cnt}.dcd", write_freq)
dataReporter = StateDataReporter(sys.stdout, write_freq, totalSteps=steps,step=True, progress=True, time=True, potentialEnergy=True, kineticEnergy=True, totalEnergy=True, temperature=True, volume=True, density=True, separator='\t')
drudeReporter = DrudeTemperatureReporter(f"out/drude_temp_{cnt}.out", write_freq)
print('Simulating...')
simulation.reporters.append(dcdReporter)
simulation.reporters.append(dataReporter)
simulation.reporters.append(drudeReporter)
simulation.step(steps)


#write restart file
state = simulation.context.getState( getPositions=True, getVelocities=True )
with open(f'traj/npt_{cnt}.rst', 'w') as f:
    f.write(XmlSerializer.serialize(state))

#crd = simulation.context.getState(getPositions=True).getPositions()
#PDBFile.writeFile(psf.topology, crd, open('trans_equil.pdb', 'w'))
