# This file was produced by https://github.com/ai-1st/dotprompt and shouldn't be edited directly.

import streamlit as st
import boto3
import matplotlib.pyplot as plt
import time
from concurrent.futures import ThreadPoolExecutor

def invoke_lambda(client, function_name, memory):
    try:
        response = client.update_function_configuration(
            FunctionName=function_name,
            MemorySize=memory
        )
        time.sleep(5)  # Wait for the update to propagate
        start = time.time()
        response = client.invoke(FunctionName=function_name)
        duration = (time.time() - start) * 1000  # Convert to milliseconds
        return memory, duration
    except Exception as e:
        st.error(f"Error invoking Lambda with {memory}MB: {str(e)}")
        return memory, None

def analyze_lambda(function_arn, aws_access_key, aws_secret_key, aws_region, memory_configs):
    client = boto3.client('lambda',
                          aws_access_key_id=aws_access_key,
                          aws_secret_access_key=aws_secret_key,
                          region_name=aws_region)

    results = []
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(invoke_lambda, client, function_arn, memory) for memory in memory_configs]
        for future in futures:
            memory, duration = future.result()
            if duration is not None:
                results.append((memory, duration))

    return results

def plot_results(results):
    memories, durations = zip(*results)
    
    fig, ax1 = plt.subplots()
    
    ax1.set_xlabel('Memory (MB)')
    ax1.set_ylabel('Duration (ms)', color='tab:blue')
    ax1.plot(memories, durations, color='tab:blue')
    ax1.tick_params(axis='y', labelcolor='tab:blue')
    
    ax2 = ax1.twinx()
    costs = [duration/1000 * memory/1024 * 0.0000166667 for memory, duration in results]  # AWS Lambda pricing formula
    ax2.set_ylabel('Estimated Cost ($)', color='tab:orange')
    ax2.plot(memories, costs, color='tab:orange')
    ax2.tick_params(axis='y', labelcolor='tab:orange')
    
    plt.title('Lambda Performance vs Cost')
    st.pyplot(fig)

    min_duration = min(durations)
    min_cost = min(costs)
    best_performance = next(mem for mem, dur in results if dur == min_duration)
    best_cost = next(mem for mem, _ in results if costs[results.index((mem, _))] == min_cost)
    
    st.write(f"Best configuration for performance: {best_performance}MB (Duration: {min_duration:.2f}ms)")
    st.write(f"Best configuration for cost: {best_cost}MB (Cost: ${min_cost:.8f})")

st.title('AWS Lambda Right-Sizing Tool')

function_arn = st.text_input('Lambda Function ARN')
aws_access_key = st.text_input('AWS Access Key')
aws_secret_key = st.text_input('AWS Secret Key', type='password')
aws_region = st.text_input('AWS Region')

memory_options = [128, 256, 512, 1024, 2048, 4096, 8192, 10240]
selected_memories = st.multiselect('Select memory configurations to test (MB)', memory_options, default=[128, 512, 1024, 2048])

if st.button('Analyze Lambda'):
    if function_arn and aws_access_key and aws_secret_key and aws_region and selected_memories:
        with st.spinner('Analyzing Lambda function...'):
            results = analyze_lambda(function_arn, aws_access_key, aws_secret_key, aws_region, selected_memories)
            if results:
                plot_results(results)
            else:
                st.error('No valid results obtained. Please check your inputs and try again.')
    else:
        st.error('Please fill in all fields and select at least one memory configuration.')