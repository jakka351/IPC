using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;

namespace Lzss
{
	public static class LzssLibrary
	{
		private const int LSZZWindow = 1024;

		public static byte[] SubByteArray(byte[] Input, int start, int length)
		{
			byte[] Output = new byte[length];
			if (Input.Length < (start + length))
				return null;
			else
			{
				for (int i = 0; i < length; i++)
				{
					Output[i] = Input[start + i];
				}
				return Output;
			}
		}

		public static ushort CreateCRC16(byte[] paramArray, byte DataFormatIdentifier)
		{
			LZSS lzss = new LZSS();

			if (DataFormatIdentifier == 0xFF || ((DataFormatIdentifier & 0x10) == 0x00)) //Not Compressed
			{
				return CRC16(paramArray);
			}
			else // Compressed
			{
				return CRC16(lzss.LZSS_ExpandData(paramArray));
			}
		}

		public static string CreateStringCRC16(byte[] paramArray, byte DataFormatIdentifier)
		{
			ushort shortResult = CreateCRC16(paramArray, DataFormatIdentifier);
			return shortResult.ToString("x4").ToUpper();
		}

		public static byte[] CreateByteCRC16(byte[] paramArray, byte DataFormatIdenfitifer)
		{
			string strResult = CreateStringCRC16(paramArray, DataFormatIdenfitifer);
			if (strResult.Length != 4)
				return null;
			else
			{
				byte[] Result = new byte[2];
				Result[0] = Convert.ToByte(strResult.Substring(0, 2), 16);
				Result[1] = Convert.ToByte(strResult.Substring(2, 2), 16);
				return Result;
			}
		}

		public static uint CreateCRC32(byte[] paramArray)
		{
			uint num = 3988292384u;
			uint[] array = new uint[256];
			uint num2;
			for (int i = 0; i < 256; i++)
			{
				num2 = (uint) i;
				for (int j = 8; j > 0; j--)
				{
					if ((num2 & 1u) > 0u)
					{
						num2 = (num2 >> 1 ^ num);
					}
					else
					{
						num2 >>= 1;
					}
				}
				array[i] = num2;
			}
			num2 = 4294967295u;
			for (int i = 0; i < paramArray.Length; i++)
			{
				num2 = ((num2 >> 8 & 16777215u) ^ array[(int) ((num2 ^ (uint) paramArray[i]) & 255u)]);
			}
			return ~num2;
		}

		public static byte[] intToByte(uint Input, int Length)
		{
			uint Mark = 0xFF;
			for (int i = 1; i < Length; i++)
				Mark = (Mark << 8) + 0xFF;
			if (Mark != 0 && Input > Mark)
				return null;
			else
			{
				byte[] Result = new byte[Length];
				for (int i = 0; i < Length; i++)
				{
					Result[i] = (byte) ((Input >> (Length - 1 - i) * 8) & 0xFF);
				}
				return Result;
			}
		}

		public static uint ByteToInt(byte[] Input)
		{
			if (Input.Length > 4)
				return 0;
			else
			{
				uint Result = 0;
				for (int i = 0; i < Input.Length; i++)
					Result = Result + (uint) ((Input[Input.Length - 1 - i] << (i * 8)));

				return Result;
			}
		}

		public static string FormatUintToHex(uint Input, int Length)
		{
			string Result = "";
			Result = Convert.ToString(Input, 16);
			while (Result.Length < Length)
				Result = "0" + Result;
			return "0x" + Result.ToUpper();
		}


		public static ushort CRC16(byte[] paramArray)
		{
			ushort[] array = new ushort[]
			{
				0,
				4129,
				8258,
				12387,
				16516,
				20645,
				24774,
				28903,
				33032,
				37161,
				41290,
				45419,
				49548,
				53677,
				57806,
				61935,
				4657,
				528,
				12915,
				8786,
				21173,
				17044,
				29431,
				25302,
				37689,
				33560,
				45947,
				41818,
				54205,
				50076,
				62463,
				58334,
				9314,
				13379,
				1056,
				5121,
				25830,
				29895,
				17572,
				21637,
				42346,
				46411,
				34088,
				38153,
				58862,
				62927,
				50604,
				54669,
				13907,
				9842,
				5649,
				1584,
				30423,
				26358,
				22165,
				18100,
				46939,
				42874,
				38681,
				34616,
				63455,
				59390,
				55197,
				51132,
				18628,
				22757,
				26758,
				30887,
				2112,
				6241,
				10242,
				14371,
				51660,
				55789,
				59790,
				63919,
				35144,
				39273,
				43274,
				47403,
				23285,
				19156,
				31415,
				27286,
				6769,
				2640,
				14899,
				10770,
				56317,
				52188,
				64447,
				60318,
				39801,
				35672,
				47931,
				43802,
				27814,
				31879,
				19684,
				23749,
				11298,
				15363,
				3168,
				7233,
				60846,
				64911,
				52716,
				56781,
				44330,
				48395,
				36200,
				40265,
				32407,
				28342,
				24277,
				20212,
				15891,
				11826,
				7761,
				3696,
				65439,
				61374,
				57309,
				53244,
				48923,
				44858,
				40793,
				36728,
				37256,
				33193,
				45514,
				41451,
				53516,
				49453,
				61774,
				57711,
				4224,
				161,
				12482,
				8419,
				20484,
				16421,
				28742,
				24679,
				33721,
				37784,
				41979,
				46042,
				49981,
				54044,
				58239,
				62302,
				689,
				4752,
				8947,
				13010,
				16949,
				21012,
				25207,
				29270,
				46570,
				42443,
				38312,
				34185,
				62830,
				58703,
				54572,
				50445,
				13538,
				9411,
				5280,
				1153,
				29798,
				25671,
				21540,
				17413,
				42971,
				47098,
				34713,
				38840,
				59231,
				63358,
				50973,
				55100,
				9939,
				14066,
				1681,
				5808,
				26199,
				30326,
				17941,
				22068,
				55628,
				51565,
				63758,
				59695,
				39368,
				35305,
				47498,
				43435,
				22596,
				18533,
				30726,
				26663,
				6336,
				2273,
				14466,
				10403,
				52093,
				56156,
				60223,
				64286,
				35833,
				39896,
				43963,
				48026,
				19061,
				23124,
				27191,
				31254,
				2801,
				6864,
				10931,
				14994,
				64814,
				60687,
				56684,
				52557,
				48554,
				44427,
				40424,
				36297,
				31782,
				27655,
				23652,
				19525,
				15522,
				11395,
				7392,
				3265,
				61215,
				65342,
				53085,
				57212,
				44955,
				49082,
				36825,
				40952,
				28183,
				32310,
				20053,
				24180,
				11923,
				16050,
				3793,
				7920
			};
			ushort num = 65535;
			for (int i = 0; i < paramArray.Length; i++)
			{
				ushort num2 = (ushort) ((int) num >> 8 ^ (paramArray[i]));
				num = (ushort) ((int) num << 8 ^ (int) array[(int) num2]);
			}
			return num;
		}


		private class BitQuery
		{
			public List<byte> Data = new List<byte>();
			public int ReadPoint = 0;
			public int WritePoint = 0;

			public BitQuery(byte[] mData)
			{
				ReadPoint = 0;
				for (int i = 0; i < mData.Length; i++)
				{
					Data.Add(mData[i]);
				}
				WritePoint = mData.Length * 8;
			}

			public BitQuery()
			{
				ReadPoint = 0;
				WritePoint = 0;
			}

			public int GetBit()
			{
				if (ReadPoint == Data.Count * 8)
				{
					return -1;
				}
				int Result = 0;
				int CurrentByte = ReadPoint / 8;
				int CurrentBit = Convert.ToByte(ReadPoint % 8);
				int Mask = 0x01;
				for (int i = 0; i < 7 - CurrentBit; i++)
				{
					Mask = Mask << 1;
				}


				if ((Data[CurrentByte] & Mask) == 0)
				{
					Result = 0;
				}
				else
				{
					Result = 1;
				}

				ReadPoint++;

				return Result;
			}


			public int GetByte()
			{
				return (GetBit(8));
			}

			public int GetBit(int mCount)
			{
				if ((ReadPoint + mCount) > Data.Count * 8)
				{
					return -1;
				}
				int Result = GetBit();
				for (int i = 0; i < mCount - 1; i++)
				{
					Result = Result << 1;
					Result = Result + GetBit();
				}
				return Result;
			}


			public bool PutBit(int Value)
			{
				bool Result = false;

				if (Value == 0 || Value == 1)
				{
					int ByteToAdd = WritePoint / 8;
					int BitToAdd = WritePoint % 8;
					//If need to Generate a new bit
					if ((ByteToAdd == Data.Count) && ((BitToAdd == 0)))
					{
						Data.Add(0x00);
					}

					int Mask = 1 << (7 - BitToAdd);
					Mask = ~Mask;


					Data[ByteToAdd] = (byte) ((Convert.ToInt32(Data[ByteToAdd]) & Mask) + (Value << (7 - BitToAdd)));

					WritePoint++;
					Result = true;
				}
				else
				{
					Result = false;
				}
				return Result;
			}

			public bool PutBits(int Value, int Length)
			{
				bool Result = false;

				string t = Convert.ToString(Value, 2);
				if (t.Length > Length)
				{
					Result = false;
				}
				else
				{
					Result = true;
					while (t.Length < Length)
					{
						t = "0" + t;
					}
					char[] p = t.ToCharArray();
					for (int i = 0; i < t.Length; i++)
					{
						if (PutBit(ConvertBit(p[i])) == false)
						{
							Result = false;
						}
					}
				}

				return Result;
			}

			public byte[] Export()
			{
				if (Data.Count == 0)
				{
					return null;
				}
				else
				{
					return Data.ToArray();
				}
			}


			private static int ConvertBit(char mBit)
			{
				switch (mBit)
				{
					case '0':
						return 0;
					case '1':
						return 1;
					default:
						return -1;
				}
			}
		}


		public class LZSS : IDisposable
		{
			/* Constant */
			/*
 
            * Number of bits allocated to indices into the text window
 
            */

			const int LZSS_INDEX_BIT_COUNT = 10;
			/*
 
            * Number of bits allocated for the length of an encode phrase
 
            */

			const int LZSS_LENGTH_BIT_COUNT = 4;

			/*
 
            * Size of the sliding window
 
            */

			const int LZSS_WINDOW_SIZE = (1 << LZSS_INDEX_BIT_COUNT);

			/*
 
            * Number of bytes to encode a byte array.
 
            * Used to calculate if compression should be done or not
 
            */

			const int LZSS_BREAK_EVEN = ((1 + LZSS_INDEX_BIT_COUNT + LZSS_LENGTH_BIT_COUNT) / 9);

			/*
 
            * End of stream indicator
 
            */

			const int LZSS_END_OF_STREAM = 0;


			/*
 
            * Size of the look-ahead buffer
 
            */

			const int LZSS_RAW_LOOK_AHEAD_SIZE = 1 << LZSS_LENGTH_BIT_COUNT;

			/*
 
            * The real look-ahead size, e.g. the maximum number of bytes to match
 
            */

			const int LZSS_LOOK_AHEAD_SIZE = (LZSS_RAW_LOOK_AHEAD_SIZE + LZSS_BREAK_EVEN);
			/*
 
            * Value of the tree root
 
            */

			const int LZSS_TREE_ROOT = LZSS_WINDOW_SIZE;

			/*
 
            * Null index for the tree structure
 
            */

			const int UNUSED = 0;

			const int LZSS_END_OF_INPUT_STREAM = -1;


			//Compress variable
			private BinaryTree[] tree = new BinaryTree[LZSS_WINDOW_SIZE + 1];

			private int[] LZSS_window = new int[LZSS_WINDOW_SIZE];


			public byte[] LZSS_ExpandData(byte[] mInput)
			{
				/** Current window position */

				int winPos = 1;

				/** Byte to write to output buffer */

				byte outByte = 0;

				/** Length of the data match found */

				int matchLen = 0;

				/** Position in the window of the data match */

				int matchPos = 0;

				/** Indicator of End Of Stream reached */

				bool eosReached = false;


				//Private Virable

				BitQuery BQ = new BitQuery(mInput);

				List<byte> Result = new List<byte>();

				byte[] LZSS_window = new byte[LZSS_WINDOW_SIZE];

				try
				{
					while (!eosReached)

					{
						/* If next bit is 1, next byte is uncompressed*/

						if (BQ.GetBit() == 1)

						{
							/* Get uncompressed byte */

							outByte = Convert.ToByte(BQ.GetByte());

							/* Output byte*/

							Result.Add(outByte);

							/* Add byte in window */

							LZSS_window[winPos] = outByte;

							/* Increase window position */

							winPos = (winPos + 1) & (LZSS_WINDOW_SIZE - 1);
						}
						/* If next bit is 0, compressed data follows */

						else

						{
							/* Get compressed data as window position of match*/

							matchPos = BQ.GetBit(LZSS_INDEX_BIT_COUNT);

							/* If end of stream, exit */

							if (matchPos == LZSS_END_OF_STREAM)

							{
								eosReached = true;
							}

							else

							{
								/* Get length of string match */

								matchLen = BQ.GetBit(LZSS_LENGTH_BIT_COUNT);

								/* Add break even + 1 to get the correct length. Length zero and
 
                                * the break even value are subtracted from the length during
 
                                * compression to save space. */

								matchLen = matchLen + (LZSS_BREAK_EVEN + 1);

								/* For every byte in match */

								for (int i = 0; i < matchLen; i++)

								{
									/* Get matching byte from window */

									outByte = LZSS_window[(matchPos + i) & (LZSS_WINDOW_SIZE - 1)];

									/* Output byte */

									Result.Add(outByte);

									/* Add matched byte to current window position */

									LZSS_window[winPos] = outByte;

									/* Increase window position */

									winPos = (winPos + 1) & (LZSS_WINDOW_SIZE - 1);
								}
							}
						}
					}
				}
				catch
				{
					return null;
				}


				return Result.ToArray<byte>();
			}


			/*
 
            *-------------------------------------------------------------------------------
 
            * 3.1 LZSS_InitTree
 
            *-------------------------------------------------------------------------------
 
            *
 
            * LZSS Initialize tree
 
            *
 
            * Initialize the binary tree used by the compression to
 
            * keep track of previously compressed byte arrays
 
            *
 
            * param rootChild Root node to the tree
 
            *
 
            * return Void
 
            *
 
            */

			private void LZSS_InitTree(int rootChild)

			{
				/* Add a root child to initialize the tree */

				tree[LZSS_TREE_ROOT].parent = UNUSED;

				tree[LZSS_TREE_ROOT].smallChild = UNUSED;

				tree[LZSS_TREE_ROOT].largeChild = rootChild;

				/* Set child parent to the tree root */

				tree[rootChild].parent = LZSS_TREE_ROOT;

				tree[rootChild].largeChild = UNUSED;

				tree[rootChild].smallChild = UNUSED;
			}


			/*
 
            *-------------------------------------------------------------------------------
 
            * 3.2 LZSS_ContractNode
 
            *-------------------------------------------------------------------------------
 
            *
 
            * LZSS contract node
 
            *
 
            * Replace a node with another node already in the tree. This function assumes
 
            * that newNode is a child to the old node.
 
            *
 
            * param oldNode Node to remove
 
            * param newNode Node to move to the oldNode position
 
            *
 
            * return Void
 
            *
 
            */
			private void LZSS_ContractNode(int oldNode, int newNode)

			{
				/* Move the parent node to the new node */

				tree[newNode].parent = tree[oldNode].parent;

				/* Change the parent on the child node */

				if (tree[tree[oldNode].parent].largeChild == oldNode)

				{
					tree[tree[oldNode].parent].largeChild = newNode;
				}

				else

				{
					tree[tree[oldNode].parent].smallChild = newNode;
				}

				/* Detach the old node */

				tree[oldNode].parent = UNUSED;

				tree[oldNode].smallChild = UNUSED;

				tree[oldNode].largeChild = UNUSED;
			}


			/*
 
            *-------------------------------------------------------------------------------
 
            * 3.3 LZSS_ReplaceNode
 
            *-------------------------------------------------------------------------------
 
            *
 
            * LZSS replace node
 
            *
 
            * Replace a node with a new node that was not previously in the tree
 
            *
 
            * param oldNode Node to remove
 
            * param newNode New node not previously in the tree
 
            *
 
            * return Void
 
            *
 
            */
			private void LZSS_ReplaceNode(int oldNode, int newNode)

			{
				/* If the old node is the smallChild*/

				if (tree[tree[oldNode].parent].smallChild == oldNode)

				{
					/* Set the new node as smallChild*/

					tree[tree[oldNode].parent].smallChild = newNode;
				}

				else

				{
					/* Else set the new node as largeChild*/

					tree[tree[oldNode].parent].largeChild = newNode;
				}

				/* Insert the old node at the new node index in the tree array*/

				tree[newNode] = tree[oldNode];

				/* Set the small child parent to the new node*/

				tree[tree[newNode].smallChild].parent = newNode;

				/* Set the large child parent to the new node*/

				tree[tree[newNode].largeChild].parent = newNode;

				/* Detach the old node */

				tree[oldNode].parent = UNUSED;

				tree[oldNode].smallChild = UNUSED;

				tree[oldNode].largeChild = UNUSED;
			}


			/*
 
            *-------------------------------------------------------------------------------
 
            * 3.4 LZSS_FindNextNode
 
            *-------------------------------------------------------------------------------
 
            *
 
            * LZSS find node
 
            *
 
            * Find the largest node under the argument node. Used when deleting
 
            * a node. This routine assumes that the argument node has a smaller child.
 
            *
 
            * param node Node to search from
 
            *
 
            * return largest node under the argument node
 
            *
 
            */
			private int LZSS_FindNextNode(int node)

			{
				int next = UNUSED;

				/* Start at the small child of the node*/

				next = tree[node].smallChild;

				/* And find the largest node under the small child*/

				while (tree[next].largeChild != UNUSED)

				{
					next = tree[next].largeChild;
				}

				return (next);
			}


			/*
 
            *-------------------------------------------------------------------------------
 
            * 3.5 LZSS_DeleteNode
 
            *-------------------------------------------------------------------------------
 
            *
 
            * LZSS delete node
 
            *
 
            * Deletes a node from the binary tree.
 
            *
 
            * param node Node to delete
 
            *
 
            * return void
 
            *
 
            */
			private void LZSS_DeleteNode(int node)

			{
				int replNode = 0;

				/* If the large child is empty, just move up the small child*/

				if (tree[node].largeChild == UNUSED)

				{
					LZSS_ContractNode(node, tree[node].smallChild);
				}
				/* If the small child is empty, just move up the large child */

				else if (tree[node].smallChild == UNUSED)

				{
					LZSS_ContractNode(node, tree[node].largeChild);
				}
				/* Otherwise, replace the node to be deleted with the largest node on
 
                * the small child side of the tree */

				else

				{
					/* Find replacment node.
 
                    * LZSS_FindNextNode will always get the largest node on the small side
 
                    * and the found node will not have any larger child */

					replNode = LZSS_FindNextNode(node);


					/* Contract the replacement node with its small child */

					LZSS_ContractNode(replNode, tree[replNode].smallChild);


					/* Replace the node to delete with the found node */

					LZSS_ReplaceNode(node, replNode);
				}
			}


			/*
 
            *-------------------------------------------------------------------------------
 
            * 3.6 LZSS_AddNode
 
            *-------------------------------------------------------------------------------
 
            *
 
            * LZSS add node
 
            *
 
            * In this routine most of the encoder work is done. The routine adds
 
            * a new node to the binary tree. It finds the best match among all existing
 
            * nodes already in the tree and returns the length and the position of the match
 
            * If the new_node has a duplicate in the tree, the old_node is deleted, for
 
            * reasons of efficiency.
 
            *
 
            * param newNode Node to add to the binary tree (pointer to the byte array)
 
            * param matchPos Return pointer to the node position in the window
 
            *
 
            * return length of the match
 
            *
 
            */
			private int LZSS_AddNode(int newNode, ref int matchPos)

			{
				int i = 0;

				int testNode = 0;

				int delta = 0;

				int matchLen = 0;


				bool matchDone = false;

				int retVal = 0;

				/* If the new byte is END_OF_STREAM, exit */

				if (newNode == LZSS_END_OF_STREAM)

				{
					return (0);
				}

				/* Get the first node to test with */

				testNode = tree[LZSS_TREE_ROOT].largeChild;

				/* Set the length of the match to 0 */

				matchLen = 0;

				while (!matchDone)

				{
					i = 0;

					delta = 0;

					/* Look for matches in the tree. Test current test node with the new
 
                    * node until they differ */

					while ((i < LZSS_LOOK_AHEAD_SIZE) && (delta == 0))

					{
						delta = LZSS_window[LZSS_MOD_WINDOW(newNode + i)] - LZSS_window[LZSS_MOD_WINDOW(testNode + i)];


						i++;
					}

					/* If the nodes didn't match every LZSS_LOOK_AHEAD_SIZE bytes
 
                    * decrease i to get the current match length */

					if (delta != 0)

					{
						i--;
					}
					/* If i larger than previous match in the tree */

					if (i >= matchLen)

					{
						/* Set new match length to i */

						matchLen = i;

						/* Set match position to the test node position */

						matchPos = testNode;

						/* If the byte array in the look-ahead buffer is an exact match of
 
                        * the test node, replace the test node with the new node to remove
 
                        * redundant data */

						if (matchLen >= LZSS_LOOK_AHEAD_SIZE)

						{
							LZSS_ReplaceNode(testNode, newNode);

							/* Search finished */

							retVal = matchLen;

							matchDone = true;
						}
					}

					if (!matchDone)

					{
						/* If the new node is larger than the test node */

						if (delta >= 0)

						{
							/* Continue to test with the larger child */

							//child = &tree[testNode].largeChild;

							if (tree[testNode].largeChild == UNUSED)

							{
								/* Add the new node to the tree */

								tree[testNode].largeChild = newNode;

								tree[newNode].parent = testNode;

								tree[newNode].largeChild = UNUSED;

								tree[newNode].smallChild = UNUSED;

								/* Search finished */

								retVal = matchLen;

								matchDone = true;
							}

							/* Continue to test the child*/

							testNode = tree[testNode].largeChild;
						}
						/* If new node is smaller than or equal to the test node */

						else

						{
							/* Continue to test with smaller child */

							//child = &tree[testNode].smallChild;
							if (tree[testNode].smallChild == UNUSED)

							{
								/* Add the new node to the tree */

								tree[testNode].smallChild = newNode;

								tree[newNode].parent = testNode;

								tree[newNode].largeChild = UNUSED;

								tree[newNode].smallChild = UNUSED;

								/* Search finished */

								retVal = matchLen;

								matchDone = true;
							}

							/* Continue to test the child*/

							testNode = tree[testNode].smallChild;
						}

						/* If the new test node is a leaf */
					}
				}

				return retVal;
			}


			/*
 
            *-------------------------------------------------------------------------------
 
            * 4.1 LZSS_CompressData
 
            *-------------------------------------------------------------------------------
 
            *
 
            * LZSS compress data
 
            *
 
            * This routine compress data from an in buffer using the LZSS algorithm. LZSS is
 
            * a dictionary compression method where the dictionary is a sliding window. The
 
            * routine uses a look-ahead buffer and finds matches in previously read bytes
 
            * stored in a sliding window.
 
            * If a match is found an index/length pair is written to the output buffer
 
            * (index is the position in the sliding window). If no match is found the read
 
            * byte is just bypassed to the out buffer. To indicate if the data is an
 
            * index/length pair or a plain text byte a single bit is used as indicator flag
 
            * and is written to the out buffer.
 
            * To speed up the compression a binary tree is used for storing previously
 
            * compressed data.
 
            *
 
            * param inBuf Input data buffer with byte access
 
            * param outBuf output data buffer with bit access
 
            *
 
            * return void
 
            *
 
            */

			public byte[] LZSS_CompressData(byte[] inBuf)

			{
				/** Index var. for loop */

				int i = 0;

				/** Byte read from input stream */

				int inByte = 0;

				/** Number of bytes in the look head buffer */

				int aheadBytes = 0;

				/** Current position in the window */

				int winPos = 1;

				/** Number of bytes to replace in the window */

				int replCnt = 0;

				/** Length of the data match found in the window */

				int matchLen = 0;

				/** Position in the window of the data match */

				int matchPos = 0;

				/** Indicator of End Of Stream reached */

				bool eosReached = false;


				BitQuery Result = new BitQuery();
				BitQuery BQ = new BitQuery(inBuf);

				/* Start with filling up the look-ahead buffer */

				while ((aheadBytes < LZSS_LOOK_AHEAD_SIZE) && (!eosReached))

				{
					/* Get next input byte */

					inByte = BQ.GetByte();


					/* If input stream is finished, exit */

					if (inByte == LZSS_END_OF_INPUT_STREAM)

					{
						eosReached = true;
					}

					else

					{
						/* Add byte to wondow */

						LZSS_window[winPos + aheadBytes] = inByte;

						/* Increase look-ahead bytes*/

						aheadBytes = (aheadBytes + 1) & 0xFF;
					}
				}
				/* Initialize the tree */

				LZSS_InitTree(winPos);

				/* While there still are bytes in the look ahead buffer, loop */

				while (aheadBytes > 0)

				{
					/* If previously match length greater than look ahead bytes it's
 
                    * not possible to code correctly */

					if (matchLen > aheadBytes)

					{
						/* Set matched length to look-ahead buffer length */

						matchLen = aheadBytes;
					}

					/* If the match is smaller than the compressed data (position/length-
 
                    * pair) there will be negative compression so just output the byte */

					if (matchLen <= LZSS_BREAK_EVEN)

					{
						/* Set consumed bytes in input stream to 1 */

						replCnt = 1;

						/* Indicate that next byte in output stream is uncompressed
 
                        * by output a '1' */

						Result.PutBit(1);

						/* Output uncompressed byte */

						Result.PutBits(LZSS_window[winPos], 8);
					}
					/* The match is larger than a position/length pair, compression can be
 
                    * done */

					else

					{
						/* Indicate that the following bits are compressed data by output a
 
                        * '0' */

						Result.PutBit(0);

						/* Output position in the window */

						Result.PutBits(matchPos, LZSS_INDEX_BIT_COUNT);

						/* Output the length of the match, (length is the number of bytes
 
                        * that is greater than LZSS_BREAK_EVEN) */

						Result.PutBits((matchLen - (LZSS_BREAK_EVEN + 1)),
							LZSS_LENGTH_BIT_COUNT);

						/* Set consumed bytes in input stream to the length of the match */

						replCnt = matchLen;
					}
					/* Delete consumed bytes and add new bytes in the window */

					for (i = 0; i < replCnt; i++)

					{
						/* Remove consumed byte from the window */

						LZSS_DeleteNode(LZSS_MOD_WINDOW(winPos +
						                                (UInt16) LZSS_LOOK_AHEAD_SIZE));

						/* Get next input byte */

						inByte = BQ.GetByte();

						/* If input stream is finished */

						if (inByte == LZSS_END_OF_INPUT_STREAM)

						{
							/* Decrease the look-ahead bytes */

							aheadBytes = (aheadBytes - 1) & 0xFF;
						}

						else

						{
							/* Add the new byte from the input stream to the window */

							LZSS_window[LZSS_MOD_WINDOW(winPos + LZSS_LOOK_AHEAD_SIZE)] = inByte;
						}

						/* Increase the position in the window */

						winPos = LZSS_MOD_WINDOW(winPos + 1);

						/* If there still are bytes in the look-ahead buffer */

						if (aheadBytes != 0)

						{
							/* Add byte position to the tree and get the length of the
 
                            * match */

							matchLen = LZSS_AddNode(winPos, ref matchPos);
						}
					}
				}

				/* Input stream finished, write end of stream to the output buffer
 
                * uncompressed */

				//OutputBit(outBuf, (Uint8_T)0);
				Result.PutBit(0);

				//OutputBits(outBuf, (Uint32_T)LZSS_END_OF_STREAM, LZSS_INDEX_BIT_COUNT);
				Result.PutBits(LZSS_END_OF_STREAM, LZSS_INDEX_BIT_COUNT);

				return Result.Export();
			}


			private struct BinaryTree
			{
				public int parent;

				public int smallChild;

				public int largeChild;
			}


			/*
             
            * Arithmetic modulo to get the correct index in the sliding window
 
            */
			private int LZSS_MOD_WINDOW(int mInput)
			{
				return (mInput & (LZSS_WINDOW_SIZE - 1));
			}

            public void Dispose()
            {
                tree = null;
                LZSS_window = null;
                GC.Collect();
            }
        }
	}
}