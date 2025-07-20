import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import io
import base64
import os
from langchain.chat_models import init_chat_model
import os
import urllib.parse
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langgraph.prebuilt import create_react_agent
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine,text

app= FastAPI(title="GenAI LLM Agent")

if not os.environ.get("GOOGLE_API_KEY"):
  os.environ["GOOGLE_API_KEY"] ="AIzaSyCaWMMK0E1NmKW7raaN2I0jh78s89h2LTk"

llm = init_chat_model("gemini-2.0-flash", model_provider="google_genai")

def get_db_url():
    db_url = ""
    try:
        db_user = os.getenv("POSTGRES_USER", default=None)
        db_password = urllib.parse.quote_plus(
            os.getenv("POSTGRES_PASSWORD", default=None)
        )
        db_host = "postgres_db"
        db_port ="5432"
        db_name = os.getenv("POSTGRES_DB", default=None)
        db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        return db_url
    except EnvironmentError as e:
        print(f"An error occurred while getting the database URL: {str(e)}")
    except Exception as e:
        print(f"An error occurred while getting the database URL: {str(e)}")

# Create the database engine
DATABASE_URL = get_db_url()
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
)
db = SQLDatabase.from_uri(DATABASE_URL)




toolkit = SQLDatabaseToolkit(db=db, llm=llm)

tools = toolkit.get_tools()
system_message = """
You are an agent designed to interact with a SQL database.
Given an input question, create a syntactically correct {dialect} query to run,
then look at the results of the query and return the answer. Unless the user
specifies a specific number of examples they wish to obtain, always limit your
query to at most {top_k} results.

You can order the results by a relevant column to return the most interesting
examples in the database. Never query for all the columns from a specific table,
only ask for the relevant columns given the question.

You MUST double check your query before executing it. If you get an error while
executing a query, rewrite the query and try again.

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the
database.

To start you should ALWAYS look at the tables in the database to see what you
can query. Do NOT skip this step.

Then you should query the schema of the most relevant tables.
""".format(
    dialect="PostgreSQL",
    top_k=5,
)



agent_executor = create_react_agent(llm, tools, prompt=system_message)

# Define request schema
class QueryRequest(BaseModel):
    question: str

@app.post("/query")
async def query(request: QueryRequest):
    question = request.question
    response = ""

    # Stream the steps and accumulate the final message
    for step in agent_executor.stream(
        {"messages": [{"role": "user", "content": question}]},
        stream_mode="values",
    ):
        response = step["messages"][-1].content

    return {"question": question, "answer": response}

@app.post("/visualise")
def query(vendor_id: str):
    try:
        query = text("""
            SELECT *
            FROM "ORDERS"
            WHERE data->>'vendor_id' = :vendor_id
        """)

        with engine.begin() as conn:
            result = conn.execute(query, {"vendor_id": vendor_id}).mappings()
            rows = result.fetchall()

            if not rows:
                raise HTTPException(status_code=404, detail="Vendor not found")

            # Extract the JSON data column
            json_data = [row['data'] for row in rows]

            # Build DataFrames
            records = []
            sku_records = []

            for order in json_data:
                date = order["timestamp"][:10]
                order_id = order["order_id"]
                revenue = sum(item["qty"] * item["unit_price"] for item in order["items"])

                records.append({
                    "vendor_id": vendor_id,
                    "order_id": order_id,
                    "date": date,
                    "revenue": revenue
                })

                for item in order["items"]:
                    sku_records.append({
                        "vendor_id": vendor_id,
                        "sku": item["sku"],
                        "qty": item["qty"],
                        "revenue": item["qty"] * item["unit_price"],
                        "date": date
                    })

            df_orders = pd.DataFrame(records)
            df_items = pd.DataFrame(sku_records)
            print(df_orders.head(5))
            print(df_items.head(5))

            # Daily Summary
            daily_summary = df_orders.groupby("date").agg(
                total_revenue=pd.NamedAgg(column="revenue", aggfunc="sum"),
                total_orders=pd.NamedAgg(column="order_id", aggfunc="count")
            ).reset_index()

            # Top SKUs
            top_skus = df_items.groupby("sku")["qty"].sum().sort_values(ascending=False).head(5).reset_index()

            # Plotting
            sns.set(style="whitegrid")
            fig, axes = plt.subplots(3, 1, figsize=(12, 12))

            # Revenue Trend
            sns.lineplot(data=daily_summary, x="date", y="total_revenue", ax=axes[0], marker="o", color="green")
            axes[0].set_title(f"Vendor {vendor_id} - Daily Revenue")
            axes[0].tick_params(axis='x', rotation=45)

            # Order Volume Trend
            sns.lineplot(data=daily_summary, x="date", y="total_orders", ax=axes[1], marker="o", color="blue")
            axes[1].set_title(f"Vendor {vendor_id} - Daily Order Volume")
            axes[1].tick_params(axis='x', rotation=45)

            # Top SKUs by Quantity
            sns.barplot(data=top_skus, x="sku", y="qty", ax=axes[2], palette="magma")
            axes[2].set_title(f"Vendor {vendor_id} - Top SKUs by Quantity")
            axes[2].set_ylabel("Total Quantity")

            plt.tight_layout()

            # Save to buffer
            buf = io.BytesIO()
            plt.savefig(buf, format="png")
            plt.close(fig)
            buf.seek(0)

            # Encode to base64
            image_base64 = base64.b64encode(buf.read()).decode("utf-8")

            return {"vendor_id": vendor_id, "visualisation_base64": image_base64}

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))